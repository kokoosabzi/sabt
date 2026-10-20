from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Operation, OperationParty, OperationType, OperationVersion, ParentContract, PartyRole, Permission, Person, Project, ProjectAccess, ProjectPerson,
    ProjectProperty, Property, Role, RolePermission, User, UserRole,
)
from app.contracts.service import (
    ParentContractConflictError, ParentContractNotFoundError, ParentContractValidationError, create_parent_contract, get_parent_contract_history, set_project_contract_code,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed_context(db, *, contract_code="76", associated=True, property_linked=True):
    now = datetime.now(timezone.utc)
    user = User(username="contract-tester", password_hash="unused", display_name="Contract Tester",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="TEST", contract_code=contract_code, name="Test Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    person = Person(first_name="Initial", last_name="Owner", created_at=now, updated_at=now,
                    version=1, is_active=True)
    prop = Property(unit_number="101", created_at=now, updated_at=now, version=1, is_active=True)
    role = Role(code="contract-admin", name="Contract Admin", active=True)
    permission = Permission(code="parent_contract.create", name="Create Parent Contract")
    project_edit = Permission(code="project.edit", name="Edit Project")
    view_permission = Permission(code="parent_contract.view", name="View Parent Contract")
    db.add_all([user, project, person, prop, role, permission, project_edit, view_permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        RolePermission(role_id=role.id, permission_id=project_edit.id),
        RolePermission(role_id=role.id, permission_id=view_permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
    ])
    if associated:
        db.add(ProjectPerson(project_id=project.id, person_id=person.id, active=True,
                             created_at=now, updated_at=now))
    if property_linked:
        db.add(ProjectProperty(project_id=project.id, property_id=prop.id, active=True,
                               created_at=now, updated_at=now))
    db.flush()
    return user, project, person, prop


def test_create_parent_contract_preserves_six_digit_number_and_leading_zeroes(db):
    user, project, person, prop = seed_context(db)
    record = create_parent_contract(db, user, project.id, "0123", person.id, prop.id)
    assert record.contract_number == "760123"
    assert record.suffix == "0123"
    assert record.initial_person_id == person.id
    assert record.property_id == prop.id
    assert record.status == "ACTIVE"


def test_create_parent_contract_rejects_missing_project_code(db):
    user, project, person, _ = seed_context(db, contract_code=None)
    with pytest.raises(ParentContractValidationError, match="project_contract_code_required"):
        create_parent_contract(db, user, project.id, "0123", person.id)
    assert db.scalar(select(ParentContract.id)) is None


def test_create_parent_contract_rejects_unassociated_initial_person(db):
    user, project, person, _ = seed_context(db, associated=False)
    with pytest.raises(ParentContractValidationError, match="initial_person_not_associated_with_project"):
        create_parent_contract(db, user, project.id, "0123", person.id)
    assert db.scalar(select(ParentContract.id)) is None


def test_create_parent_contract_rejects_unassociated_property(db):
    user, project, person, prop = seed_context(db, property_linked=False)
    with pytest.raises(ParentContractValidationError, match="property_not_associated_with_project"):
        create_parent_contract(db, user, project.id, "0123", person.id, prop.id)
    assert db.scalar(select(ParentContract.id)) is None


def test_create_parent_contract_rejects_duplicate_suffix(db):
    user, project, person, _ = seed_context(db)
    create_parent_contract(db, user, project.id, "0123", person.id)
    with pytest.raises(ParentContractConflictError, match="parent_contract_suffix_exists"):
        create_parent_contract(db, user, project.id, "0123", person.id)
    assert len(db.scalars(select(ParentContract)).all()) == 1


@pytest.mark.parametrize("suffix", ["123", "12A4", " 123", "12345"])
def test_create_parent_contract_rejects_invalid_suffix(db, suffix):
    user, project, person, _ = seed_context(db)
    with pytest.raises(ParentContractValidationError, match="parent_contract_suffix_invalid"):
        create_parent_contract(db, user, project.id, suffix, person.id)
    assert db.scalar(select(ParentContract.id)) is None


def test_create_parent_contract_requires_project_access(db):
    user, project, person, _ = seed_context(db)
    access = db.get(ProjectAccess, (user.id, project.id))
    db.delete(access)
    db.flush()
    with pytest.raises(PermissionError, match="forbidden"):
        create_parent_contract(db, user, project.id, "0123", person.id)
    assert db.scalar(select(ParentContract.id)) is None


def test_project_contract_code_can_be_changed_before_first_parent_contract(db):
    user, project, _, _ = seed_context(db)
    updated = set_project_contract_code(db, user, project.id, "77", expected_version=project.version)
    assert updated.contract_code == "77"
    assert updated.version == 2


def test_project_contract_code_is_immutable_after_first_parent_contract(db):
    user, project, person, _ = seed_context(db)
    create_parent_contract(db, user, project.id, "0123", person.id)
    with pytest.raises(ParentContractConflictError, match="project_contract_code_immutable"):
        set_project_contract_code(db, user, project.id, "77", expected_version=project.version)
    db.refresh(project)
    assert project.contract_code == "76"


def test_project_contract_code_rejects_stale_version_and_invalid_code(db):
    user, project, _, _ = seed_context(db)
    with pytest.raises(ParentContractConflictError, match="stale_project"):
        set_project_contract_code(db, user, project.id, "77", expected_version=project.version - 1)
    with pytest.raises(ParentContractValidationError, match="project_contract_code_invalid"):
        set_project_contract_code(db, user, project.id, "09", expected_version=project.version)
    db.refresh(project)
    assert project.contract_code == "76"



def test_parent_contract_history_lists_numbered_transfers_and_drafts(db):
    user, project, person, prop = seed_context(db)
    parent = create_parent_contract(db, user, project.id, "0123", person.id, prop.id)
    now = datetime.now(timezone.utc)
    operation_type = OperationType(
        code="TRANSFER", name="Transfer", active=True, system_defined=True,
        created_at=now, updated_at=now,
    )
    db.add(operation_type)
    db.flush()
    parent.next_transfer_sequence = 2
    buyer = Person(first_name="Buyer", last_name="Transferee", created_at=now, updated_at=now,
                   version=1, is_active=True)
    buyer_role = PartyRole(code="BUYER_TRANSFEREE", name="Buyer / Transferee", active=True,
                           system_defined=True, created_at=now, updated_at=now)
    db.add_all([buyer, buyer_role])
    db.flush()
    db.add(ProjectPerson(project_id=project.id, person_id=buyer.id, active=True,
                         created_at=now, updated_at=now))
    finalized = Operation(
        project_id=project.id, operation_type_id=operation_type.id, status="FINALIZED",
        current_workflow_state="FINALIZED", property_id=prop.id, created_by=user.id,
        finalized_by=user.id, created_at=now, updated_at=now, finalized_at=now,
        version=2, current_version_number=1, parent_contract_id=parent.id,
        transfer_sequence=1, child_contract_number="760123/1",
    )
    draft = Operation(
        project_id=project.id, operation_type_id=operation_type.id, status="DRAFT",
        current_workflow_state="DRAFT", property_id=prop.id, created_by=user.id,
        created_at=now, updated_at=now, version=1, current_version_number=0,
        parent_contract_id=parent.id,
    )
    db.add_all([finalized, draft])
    db.flush()
    second_buyer = Person(first_name="Second", last_name="Buyer", created_at=now, updated_at=now,
                          version=1, is_active=True)
    db.add(second_buyer)
    db.flush()
    db.add(ProjectPerson(project_id=project.id, person_id=second_buyer.id, active=True,
                         created_at=now, updated_at=now))
    second_transfer = Operation(
        project_id=project.id, operation_type_id=operation_type.id, status="FINALIZED",
        current_workflow_state="FINALIZED", property_id=prop.id, created_by=user.id,
        finalized_by=user.id, created_at=now, updated_at=now, finalized_at=now,
        version=2, current_version_number=1, parent_contract_id=parent.id,
        transfer_sequence=2, child_contract_number="760123/2",
    )
    db.add(second_transfer)
    db.flush()
    db.add_all([
        OperationVersion(operation_id=finalized.id, version_number=1, created_by=user.id,
                         created_at=now, finalized_at=now, snapshot_json="{}", hash="test-hash-1"),
        OperationParty(project_id=project.id, operation_id=finalized.id, person_id=buyer.id, role_id=buyer_role.id,
                       sequence_no=1, created_at=now, updated_at=now, version=1),
        OperationVersion(operation_id=second_transfer.id, version_number=1, created_by=user.id,
                         created_at=now, finalized_at=now, snapshot_json="{}", hash="test-hash-2"),
        OperationParty(project_id=project.id, operation_id=second_transfer.id, person_id=second_buyer.id, role_id=buyer_role.id,
                       sequence_no=1, created_at=now, updated_at=now, version=1),
    ])
    db.flush()

    history = get_parent_contract_history(db, user, "760123")
    assert history["parent"]["contract_number"] == "760123"
    assert [row["child_contract_number"] for row in history["transfers"]] == ["760123/1", "760123/2", None]
    assert [row["status"] for row in history["transfers"]] == ["FINALIZED", "FINALIZED", "DRAFT"]
    assert history["current_owner"]["source"] == "latest_valid_finalized_transfer"
    assert history["current_owner"]["child_contract_number"] == "760123/2"
    assert history["current_owner"]["people"][0]["person_id"] == second_buyer.id


def test_parent_contract_history_ignores_operations_mislinked_from_another_project(db):
    user, project, person, _ = seed_context(db)
    parent = create_parent_contract(db, user, project.id, "0123", person.id)
    now = datetime.now(timezone.utc)
    other = Project(code="OTHER", name="Other Project", status="ACTIVE",
                    timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    operation_type = OperationType(
        code="TRANSFER", name="Transfer", active=True, system_defined=True,
        created_at=now, updated_at=now,
    )
    buyer = Person(first_name="Foreign", last_name="Buyer", created_at=now, updated_at=now,
                   version=1, is_active=True)
    buyer_role = PartyRole(code="BUYER_TRANSFEREE", name="Buyer / Transferee", active=True,
                           system_defined=True, created_at=now, updated_at=now)
    db.add_all([other, operation_type, buyer, buyer_role])
    db.flush()
    foreign_operation = Operation(
        project_id=other.id, operation_type_id=operation_type.id, status="FINALIZED",
        current_workflow_state="FINALIZED", created_by=user.id, finalized_by=user.id,
        created_at=now, updated_at=now, finalized_at=now, version=2, current_version_number=1,
        parent_contract_id=parent.id, transfer_sequence=1, child_contract_number="760123/1",
    )
    db.add(foreign_operation)
    db.flush()
    db.add_all([
        OperationVersion(
            operation_id=foreign_operation.id, version_number=1, created_by=user.id,
            created_at=now, finalized_at=now, snapshot_json="{}", hash="test-hash",
        ),
        OperationParty(
            project_id=other.id, operation_id=foreign_operation.id, person_id=buyer.id, role_id=buyer_role.id,
            sequence_no=1, created_at=now, updated_at=now, version=1,
        ),
    ])
    db.flush()

    history = get_parent_contract_history(db, user, parent.contract_number)
    assert history["transfers"] == []
    assert history["current_owner"]["source"] == "initial_contract"
    assert history["current_owner"]["people"][0]["person_id"] == person.id


def test_parent_contract_history_does_not_expose_foreign_project_transferee(db):
    user, project, initial_person, _ = seed_context(db)
    parent = create_parent_contract(db, user, project.id, "0123", initial_person.id)
    now = datetime.now(timezone.utc)
    operation_type = OperationType(
        code="TRANSFER", name="Transfer", active=True, system_defined=True,
        created_at=now, updated_at=now,
    )
    buyer_role = PartyRole(code="BUYER_TRANSFEREE", name="Buyer / Transferee", active=True,
                           system_defined=True, created_at=now, updated_at=now)
    foreign_buyer = Person(first_name="Foreign", last_name="Person", national_id="FOREIGN-SECRET",
                           mobile="555-0100", created_at=now, updated_at=now, version=1, is_active=True)
    other_project = Project(code="OTHER-OWNER", name="Other Owner Project", status="ACTIVE",
                            timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    db.add_all([operation_type, buyer_role, foreign_buyer, other_project])
    db.flush()
    db.add(ProjectPerson(project_id=other_project.id, person_id=foreign_buyer.id, active=True,
                         created_at=now, updated_at=now))
    operation = Operation(
        project_id=project.id, operation_type_id=operation_type.id, status="FINALIZED",
        current_workflow_state="FINALIZED", created_by=user.id, finalized_by=user.id,
        created_at=now, updated_at=now, finalized_at=now, version=2, current_version_number=1,
        parent_contract_id=parent.id, transfer_sequence=1, child_contract_number="760123/1",
    )
    db.add(operation)
    db.flush()
    db.add_all([
        OperationVersion(operation_id=operation.id, version_number=1, created_by=user.id,
                         created_at=now, finalized_at=now, snapshot_json="{}", hash="foreign-party-test"),
        OperationParty(project_id=project.id, operation_id=operation.id, person_id=foreign_buyer.id, role_id=buyer_role.id,
                       sequence_no=1, created_at=now, updated_at=now, version=1),
    ])
    db.flush()

    history = get_parent_contract_history(db, user, parent.contract_number)
    assert history["current_owner"]["source"] == "initial_contract"
    assert history["current_owner"]["people"][0]["person_id"] == initial_person.id
    assert all(person["national_id"] != "FOREIGN-SECRET" for person in history["current_owner"]["people"])


def test_parent_contract_history_hides_initial_person_without_project_membership(db):
    user, project, initial_person, _ = seed_context(db)
    parent = create_parent_contract(db, user, project.id, "0123", initial_person.id)
    other_project = Project(code="OTHER-INITIAL", name="Other Initial Project", status="ACTIVE",
                            timezone="Asia/Tehran", created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc), version=1)
    db.add(other_project)
    db.flush()
    db.add(ProjectPerson(project_id=other_project.id, person_id=initial_person.id, active=True,
                         created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
    db.delete(db.get(ProjectPerson, (project.id, initial_person.id)))
    db.flush()

    history = get_parent_contract_history(db, user, parent.contract_number)
    assert history["parent"]["id"] == parent.id
    assert history["current_owner"]["source"] == "initial_contract"
    assert history["current_owner"]["people"] == []


def test_parent_contract_history_rejects_user_without_project_access(db):
    user, project, person, _ = seed_context(db)
    create_parent_contract(db, user, project.id, "0123", person.id)
    db.delete(db.get(ProjectAccess, (user.id, project.id)))
    db.flush()
    with pytest.raises(ParentContractNotFoundError, match="parent_contract_not_found"):
        get_parent_contract_history(db, user, "760123")
