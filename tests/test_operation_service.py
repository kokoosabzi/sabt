from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Appointment,
    AppointmentType,
    PartyRole,
    Person,
    Operation,
    OperationAppointment,
    OperationParty,
    OperationType,
    OperationVersion,
    Permission,
    Project,
    ProjectAccess,
    ProjectOperationType,
    ProjectPerson,
    ProjectProperty,
    Property,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.operations.service import ConflictError, ValidationError, add_party, create_operation, finalize_operation


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def seed_operation_context(db: Session):
    now = datetime.now(timezone.utc)
    user = User(
        username="operation-tester",
        password_hash="unused-test-hash",
        display_name="Operation Tester",
        active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    project = Project(
        code="TARGET",
        name="Target Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_project = Project(
        code="OTHER",
        name="Other Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    operation_type = OperationType(
        code="SALE",
        name="Sale",
        active=True,
        system_defined=True,
        created_at=now,
        updated_at=now,
    )
    property_record = Property(
        address="Test address",
        created_at=now,
        updated_at=now,
        version=1,
        is_active=True,
    )
    role = Role(code="creator", name="Creator", active=True)
    permission = Permission(code="operation.create", name="Create operation")
    edit_permission = Permission(code="operation.edit", name="Edit operation")
    finalize_permission = Permission(code="operation.finalize", name="Finalize operation")
    appointment_type = AppointmentType(
        code="CONSULT",
        name="Consultation",
        attendance_behavior="ATTENDANCE_ONLY",
        default_duration_minutes=30,
        active=True,
        created_at=now,
        updated_at=now,
    )
    db.add_all([user, project, other_project, operation_type, property_record, role, permission, edit_permission, finalize_permission, appointment_type])
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
            RolePermission(role_id=role.id, permission_id=edit_permission.id),
            RolePermission(role_id=role.id, permission_id=finalize_permission.id),
            UserRole(user_id=user.id, role_id=role.id, project_id=None),
            ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
            ProjectOperationType(
                project_id=project.id,
                operation_type_id=operation_type.id,
                enabled=True,
                created_at=now,
                updated_at=now,
                version=1,
            ),
            ProjectProperty(
                project_id=project.id,
                property_id=property_record.id,
                active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db.flush()

    target_appointment = Appointment(
        project_id=project.id,
        appointment_type_id=appointment_type.id,
        start_at=now + timedelta(hours=1),
        end_at=now + timedelta(hours=1, minutes=30),
        status="RESERVED",
        created_by=user.id,
        created_at=now,
        updated_at=now,
        version=1,
    )
    other_appointment = Appointment(
        project_id=other_project.id,
        appointment_type_id=appointment_type.id,
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=2, minutes=30),
        status="RESERVED",
        created_by=user.id,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add_all([target_appointment, other_appointment])
    db.flush()
    return user, project, operation_type, property_record, target_appointment, other_appointment


def test_create_operation_links_appointment_from_same_project(db: Session) -> None:
    user, project, operation_type, property_record, appointment, _ = seed_operation_context(db)

    operation = create_operation(
        db,
        user,
        project.id,
        operation_type.id,
        property_id=property_record.id,
        appointment_id=appointment.id,
    )

    assert operation.status == "DRAFT"
    link = db.get(OperationAppointment, (appointment.id, operation.id))
    assert link is not None


def test_cross_project_appointment_is_rejected_before_operation_write(db: Session) -> None:
    user, project, operation_type, property_record, _, other_appointment = seed_operation_context(db)

    with pytest.raises(ValidationError, match="appointment_project_mismatch"):
        create_operation(
            db,
            user,
            project.id,
            operation_type.id,
            property_id=property_record.id,
            appointment_id=other_appointment.id,
        )

    assert db.scalar(select(func.count()).select_from(Operation)) == 0


def test_property_must_be_associated_with_target_project(db: Session) -> None:
    user, project, operation_type, _, appointment, _ = seed_operation_context(db)
    unrelated_property = Property(
        address="Unassociated",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
        is_active=True,
    )
    db.add(unrelated_property)
    db.flush()

    with pytest.raises(ValidationError, match="property_not_associated_with_project"):
        create_operation(
            db,
            user,
            project.id,
            operation_type.id,
            property_id=unrelated_property.id,
            appointment_id=appointment.id,
        )

    assert db.scalar(select(func.count()).select_from(Operation)) == 0


def test_finalize_requires_property_and_leaves_draft_unchanged(db: Session) -> None:
    user, project, operation_type, _, _, _ = seed_operation_context(db)
    operation = create_operation(
        db,
        user,
        project.id,
        operation_type.id,
    )

    with pytest.raises(ValidationError, match="property_required"):
        finalize_operation(db, user, operation.id, expected_version=operation.version)

    db.refresh(operation)
    assert operation.status == "DRAFT"
    assert operation.finalized_at is None
    assert db.scalar(select(func.count()).select_from(OperationVersion)) == 0


def test_finalize_rejects_stale_version_without_side_effects(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(
        db,
        user,
        project.id,
        operation_type.id,
        property_id=property_record.id,
    )
    original_version = operation.version

    with pytest.raises(ConflictError, match="stale_operation"):
        finalize_operation(
            db,
            user,
            operation.id,
            expected_version=original_version - 1,
            reason="Stale client version",
        )

    db.refresh(operation)
    assert operation.status == "DRAFT"
    assert operation.finalized_at is None
    assert operation.version == original_version
    assert operation.current_version_number == 0
    assert db.scalar(select(func.count()).select_from(OperationVersion)) == 0


def test_finalize_with_property_persists_hashed_snapshot_and_rejects_repeat(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(
        db,
        user,
        project.id,
        operation_type.id,
        property_id=property_record.id,
    )
    original_version = operation.version

    version_record = finalize_operation(
        db,
        user,
        operation.id,
        expected_version=original_version,
        reason="Foundation test",
    )

    db.refresh(operation)
    assert operation.status == "FINALIZED"
    assert operation.current_workflow_state == "FINALIZED"
    assert operation.finalized_at is not None
    assert operation.current_version_number == 1
    assert operation.version == original_version + 1

    snapshot = json.loads(version_record.snapshot_json)
    assert snapshot["operation"]["id"] == operation.id
    assert snapshot["property"]["property_id"] == property_record.id
    assert version_record.hash == hashlib.sha256(
        version_record.snapshot_json.encode("utf-8")
    ).hexdigest()
    assert db.scalar(select(func.count()).select_from(OperationVersion)) == 1

    with pytest.raises(ConflictError, match="operation_already_finalized"):
        finalize_operation(db, user, operation.id, expected_version=operation.version)

    assert db.scalar(select(func.count()).select_from(OperationVersion)) == 1



def _make_party_records(db: Session, project_id: int, *, associated: bool = True, association_active: bool = True):
    now = datetime.now(timezone.utc)
    person = Person(
        first_name="Test",
        last_name="Owner",
        created_at=now,
        updated_at=now,
        version=1,
        is_active=True,
    )
    party_role = PartyRole(
        code="OWNER",
        name="Owner",
        active=True,
        system_defined=True,
        created_at=now,
        updated_at=now,
    )
    db.add_all([person, party_role])
    db.flush()
    if associated:
        db.add(
            ProjectPerson(
                project_id=project_id,
                person_id=person.id,
                active=association_active,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
    return person, party_role


def test_add_party_rejects_person_not_associated_with_operation_project(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, project.id, associated=False)

    with pytest.raises(ValidationError, match="person_not_associated_with_project"):
        add_party(db, user, operation.id, person.id, party_role.id, expected_version=operation.version)

    assert db.scalar(select(func.count()).select_from(OperationParty)) == 0
    db.refresh(operation)
    assert operation.version == 1


def test_add_party_rejects_person_associated_only_with_another_project(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    other_project = db.scalar(select(Project).where(Project.code == "OTHER"))
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, other_project.id)

    with pytest.raises(ValidationError, match="person_not_associated_with_project"):
        add_party(db, user, operation.id, person.id, party_role.id, expected_version=operation.version)

    assert db.scalar(select(func.count()).select_from(OperationParty)) == 0


def test_add_party_rejects_inactive_project_person_link(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, project.id, association_active=False)

    with pytest.raises(ValidationError, match="person_not_associated_with_project"):
        add_party(db, user, operation.id, person.id, party_role.id, expected_version=operation.version)

    assert db.scalar(select(func.count()).select_from(OperationParty)) == 0


def test_add_party_requires_positive_sequence_number(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, project.id)

    with pytest.raises(ValidationError, match="party_sequence_invalid"):
        add_party(db, user, operation.id, person.id, party_role.id, sequence_no=0,
                  expected_version=operation.version)

    assert db.scalar(select(func.count()).select_from(OperationParty)) == 0
    db.refresh(operation)
    assert operation.version == 1


def test_add_party_persists_valid_project_member_and_increments_operation_version(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, project.id)

    party = add_party(db, user, operation.id, person.id, party_role.id, expected_version=operation.version)

    assert db.get(OperationParty, party.id) is not None
    db.refresh(operation)
    assert operation.version == 2


def test_add_party_rejects_stale_version_without_side_effects(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    person, party_role = _make_party_records(db, project.id)

    with pytest.raises(ConflictError, match="stale_operation"):
        add_party(
            db, user, operation.id, person.id, party_role.id,
            expected_version=operation.version - 1,
        )

    assert db.scalar(select(func.count()).select_from(OperationParty)) == 0
    db.refresh(operation)
    assert operation.version == 1
