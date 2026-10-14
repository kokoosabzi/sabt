from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth.authorization import AuthorizationContext, authorize
from app.contracts.numbering import build_parent_contract_number, validate_parent_contract_number, validate_parent_contract_suffix, validate_project_contract_code
from app.db.models import Operation, ParentContract, Person, Project, ProjectPerson, ProjectProperty, Property, User

class ParentContractError(Exception):
    pass

class ParentContractNotFoundError(ParentContractError):
    pass

class ParentContractConflictError(ParentContractError):
    pass

class ParentContractValidationError(ParentContractError):
    pass

def create_parent_contract(db: Session, user: User, project_id: int, suffix: str,
                           initial_person_id: int, property_id: int | None = None) -> ParentContract:
    """Create a stable six-digit contract; caller owns commit/rollback."""
    authorize(db, user, "parent_contract.create", AuthorizationContext(project_id=project_id))
    project = db.get(Project, project_id)
    if project is None:
        raise ParentContractNotFoundError("project_not_found")
    if project.status != "ACTIVE":
        raise ParentContractValidationError("project_inactive")
    if project.contract_code is None:
        raise ParentContractValidationError("project_contract_code_required")
    try:
        code = validate_project_contract_code(project.contract_code)
        suffix = validate_parent_contract_suffix(suffix)
        number = build_parent_contract_number(code, suffix)
    except ValueError as exc:
        raise ParentContractValidationError(str(exc)) from exc
    person = db.get(Person, initial_person_id)
    if person is None or not person.is_active:
        raise ParentContractValidationError("initial_person_invalid")
    link = db.get(ProjectPerson, (project_id, initial_person_id))
    if link is None or not link.active:
        raise ParentContractValidationError("initial_person_not_associated_with_project")
    if property_id is not None:
        prop = db.get(Property, property_id)
        if prop is None or not prop.is_active:
            raise ParentContractValidationError("property_invalid")
        property_link = db.get(ProjectProperty, (project_id, property_id))
        if property_link is None or not property_link.active:
            raise ParentContractValidationError("property_not_associated_with_project")
    if db.scalar(select(ParentContract.id).where(ParentContract.project_id == project_id,
                                                ParentContract.suffix == suffix)) is not None:
        raise ParentContractConflictError("parent_contract_suffix_exists")
    if db.scalar(select(ParentContract.id).where(ParentContract.contract_number == number)) is not None:
        raise ParentContractConflictError("parent_contract_number_exists")
    now = datetime.now(timezone.utc)
    record = ParentContract(project_id=project_id, contract_number=number, suffix=suffix,
        initial_person_id=initial_person_id, property_id=property_id, status="ACTIVE",
        created_at=now, updated_at=now, version=1)
    db.add(record)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ParentContractConflictError("parent_contract_number_conflict") from exc
    return record


def set_project_contract_code(
    db: Session,
    user: User,
    project_id: int,
    contract_code: str,
    *,
    expected_version: int,
) -> Project:
    """Set a project's contract code, but freeze it after its first Parent Contract."""
    authorize(db, user, "project.edit", AuthorizationContext(project_id=project_id))
    project = db.get(Project, project_id)
    if project is None:
        raise ParentContractNotFoundError("project_not_found")
    if project.version != expected_version:
        raise ParentContractConflictError("stale_project")
    try:
        normalized_code = validate_project_contract_code(contract_code)
    except ValueError as exc:
        raise ParentContractValidationError(str(exc)) from exc

    existing = db.scalar(
        select(Project.id).where(
            Project.contract_code == normalized_code,
            Project.id != project_id,
        )
    )
    if existing is not None:
        raise ParentContractConflictError("project_contract_code_exists")

    has_contracts = db.scalar(
        select(ParentContract.id).where(ParentContract.project_id == project_id).limit(1)
    ) is not None
    if has_contracts and project.contract_code != normalized_code:
        raise ParentContractConflictError("project_contract_code_immutable")

    if project.contract_code != normalized_code:
        project.contract_code = normalized_code
        project.version += 1
        project.updated_at = datetime.now(timezone.utc)
        db.flush()
    return project


def get_parent_contract_history(
    db: Session,
    user: User,
    contract_number: str,
) -> dict:
    """Return an authorized Parent Contract and its linked Operation history."""
    try:
        normalized_number = validate_parent_contract_number(contract_number)
    except ValueError as exc:
        raise ParentContractValidationError(str(exc)) from exc
    parent = db.scalar(
        select(ParentContract).where(ParentContract.contract_number == normalized_number)
    )
    if parent is None:
        raise ParentContractNotFoundError("parent_contract_not_found")
    authorize(
        db,
        user,
        "parent_contract.view",
        AuthorizationContext(project_id=parent.project_id),
    )
    operations = db.scalars(
        select(Operation)
        .where(Operation.parent_contract_id == parent.id)
        .order_by(
            Operation.transfer_sequence.is_(None),
            Operation.transfer_sequence,
            Operation.created_at,
            Operation.id,
        )
    ).all()
    return {
        "parent": {
            "id": parent.id,
            "project_id": parent.project_id,
            "contract_number": parent.contract_number,
            "suffix": parent.suffix,
            "initial_person_id": parent.initial_person_id,
            "property_id": parent.property_id,
            "status": parent.status,
        },
        "transfers": [
            {
                "operation_id": operation.id,
                "operation_type_id": operation.operation_type_id,
                "status": operation.status,
                "transfer_sequence": operation.transfer_sequence,
                "child_contract_number": operation.child_contract_number,
                "property_id": operation.property_id,
                "created_at": operation.created_at,
                "finalized_at": operation.finalized_at,
                "current_version_number": operation.current_version_number,
            }
            for operation in operations
        ],
    }


def _derive_current_owner(db: Session, parent: ParentContract) -> dict:
    # Only a finalized operation with its current finalized version and at least
    # one Buyer / Transferee party is a valid ownership-changing transfer.
    latest = db.scalar(
        select(Operation)
        .join(
            OperationVersion,
            (OperationVersion.operation_id == Operation.id)
            & (OperationVersion.version_number == Operation.current_version_number)
            & (OperationVersion.finalized_at.is_not(None)),
        )
        .join(OperationParty, OperationParty.operation_id == Operation.id)
        .join(PartyRole, PartyRole.id == OperationParty.role_id)
        .where(
            Operation.parent_contract_id == parent.id,
            Operation.status == "FINALIZED",
            Operation.finalized_at.is_not(None),
            Operation.transfer_sequence.is_not(None),
            Operation.child_contract_number.is_not(None),
            Operation.current_version_number > 0,
            PartyRole.code == BUYER_TRANSFEREE_ROLE_CODE,
        )
        .order_by(Operation.transfer_sequence.desc(), Operation.finalized_at.desc(), Operation.id.desc())
    )
    if latest is None:
        person = db.get(Person, parent.initial_person_id)
        return {
            "source": "initial_contract",
            "operation_id": None,
            "child_contract_number": None,
            "people": [{"person_id": person.id, "first_name": person.first_name,
                        "last_name": person.last_name, "national_id": person.national_id,
                        "mobile": person.mobile}],
        }
    people = db.execute(
        select(Person)
        .join(OperationParty, OperationParty.person_id == Person.id)
        .join(PartyRole, PartyRole.id == OperationParty.role_id)
        .where(OperationParty.operation_id == latest.id, PartyRole.code == BUYER_TRANSFEREE_ROLE_CODE)
        .order_by(OperationParty.sequence_no, OperationParty.id)
    ).scalars().all()
    return {
        "source": "latest_valid_finalized_transfer",
        "operation_id": latest.id,
        "child_contract_number": latest.child_contract_number,
        "people": [{"person_id": p.id, "first_name": p.first_name, "last_name": p.last_name,
                    "national_id": p.national_id, "mobile": p.mobile} for p in people],
    }