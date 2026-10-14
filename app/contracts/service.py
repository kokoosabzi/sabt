from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth.authorization import AuthorizationContext, authorize
from app.contracts.numbering import build_parent_contract_number, validate_parent_contract_suffix, validate_project_contract_code
from app.db.models import ParentContract, Person, Project, ProjectPerson, ProjectProperty, Property, User

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
