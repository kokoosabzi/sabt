from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    ParentContract, Permission, Person, Project, ProjectAccess, ProjectPerson,
    ProjectProperty, Property, Role, RolePermission, User, UserRole,
)
from app.contracts.service import (
    ParentContractConflictError, ParentContractValidationError, create_parent_contract,
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
    db.add_all([user, project, person, prop, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
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
