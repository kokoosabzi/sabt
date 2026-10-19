from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
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
    ParentContract,
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
    WorkflowEvent,
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
    created_event = db.scalar(select(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "OPERATION_CREATED",
    ))
    assert created_event is not None
    assert created_event.to_status == "DRAFT"


def test_inactive_property_is_rejected_before_operation_write(db: Session) -> None:
    user, project, operation_type, _, appointment, _ = seed_operation_context(db)
    inactive_property = Property(
        address="Inactive property",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
        is_active=False,
    )
    db.add(inactive_property)
    db.flush()
    db.add(
        ProjectProperty(
            project_id=project.id,
            property_id=inactive_property.id,
            active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.flush()

    with pytest.raises(ValidationError, match="property_inactive"):
        create_operation(
            db,
            user,
            project.id,
            operation_type.id,
            property_id=inactive_property.id,
            appointment_id=appointment.id,
        )

    assert db.scalar(select(func.count()).select_from(Operation)) == 0


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


def test_finalize_rejects_property_deactivated_after_draft_creation(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    property_record.is_active = False
    db.flush()

    with pytest.raises(ValidationError, match="property_inactive"):
        finalize_operation(db, user, operation.id, expected_version=operation.version)

    db.refresh(operation)
    assert operation.status == "DRAFT"
    assert operation.finalized_at is None
    assert db.scalar(select(func.count()).select_from(OperationVersion)) == 0


def test_finalize_rejects_deactivated_project_property_association(db: Session) -> None:
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    operation = create_operation(db, user, project.id, operation_type.id, property_id=property_record.id)
    association = db.get(ProjectProperty, (project.id, property_record.id))
    association.active = False
    db.flush()

    with pytest.raises(ValidationError, match="property_not_associated_with_project"):
        finalize_operation(db, user, operation.id, expected_version=operation.version)

    db.refresh(operation)
    assert operation.status == "DRAFT"
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



def _make_transfer_operation(db: Session):
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    project.contract_code = "76"
    initial_person, party_role = _make_party_records(db, project.id)
    party_role.code = "BUYER_TRANSFEREE"
    party_role.name = "Buyer / Transferee"
    now = datetime.now(timezone.utc)
    parent = ParentContract(
        project_id=project.id, contract_number="760123", suffix="0123",
        initial_person_id=initial_person.id, property_id=property_record.id, status="ACTIVE",
        next_transfer_sequence=1, created_at=now, updated_at=now, version=1,
    )
    db.add(parent)
    db.flush()
    operation = create_operation(db, user, project.id, operation_type.id,
                                 property_id=property_record.id, parent_contract_id=parent.id)
    add_party(db, user, operation.id, initial_person.id, party_role.id, expected_version=operation.version)
    db.flush()
    return user, project, parent, operation


def test_finalized_transfer_gets_next_child_number_and_snapshot(db: Session):
    user, project, parent, operation = _make_transfer_operation(db)
    version = finalize_operation(db, user, operation.id, expected_version=operation.version)
    db.refresh(operation)
    db.refresh(parent)
    assert operation.status == "FINALIZED"
    assert operation.transfer_sequence == 1
    assert operation.child_contract_number == "760123/1"
    assert parent.next_transfer_sequence == 2
    snapshot = json.loads(version.snapshot_json)
    assert snapshot["operation"]["child_contract_number"] == "760123/1"
    assert snapshot["operation"]["transfer_sequence"] == 1


def test_each_finalized_transfer_gets_a_distinct_sequence(db: Session):
    user, project, parent, first = _make_transfer_operation(db)
    finalize_operation(db, user, first.id, expected_version=first.version)
    second = create_operation(db, user, project.id, first.operation_type_id,
                              property_id=first.property_id, parent_contract_id=parent.id)
    party = db.scalar(select(OperationParty).where(OperationParty.operation_id == first.id))
    add_party(db, user, second.id, party.person_id, party.role_id, expected_version=second.version)
    finalize_operation(db, user, second.id, expected_version=second.version)
    db.refresh(second)
    assert first.child_contract_number == "760123/1"
    assert second.child_contract_number == "760123/2"
    assert second.transfer_sequence == 2


def test_transfer_finalization_requires_a_party_without_consuming_sequence(db: Session):
    user, project, operation_type, property_record, _, _ = seed_operation_context(db)
    project.contract_code = "76"
    person, role = _make_party_records(db, project.id)
    role.code = "BUYER_TRANSFEREE"
    role.name = "Buyer / Transferee"
    now = datetime.now(timezone.utc)
    parent = ParentContract(
        project_id=project.id, contract_number="760123", suffix="0123",
        initial_person_id=person.id, property_id=property_record.id, status="ACTIVE",
        next_transfer_sequence=1, created_at=now, updated_at=now, version=1,
    )
    db.add(parent)
    db.flush()
    operation = create_operation(db, user, project.id, operation_type.id,
                                 property_id=property_record.id, parent_contract_id=parent.id)
    with pytest.raises(ValidationError, match="buyer_transferee_required"):
        finalize_operation(db, user, operation.id, expected_version=operation.version)
    db.refresh(parent)
    db.refresh(operation)
    assert parent.next_transfer_sequence == 1
    assert operation.status == "DRAFT"
    assert operation.child_contract_number is None


def test_rolling_back_transfer_finalization_releases_sequence(db: Session):
    user, project, parent, operation = _make_transfer_operation(db)
    nested = db.begin_nested()
    finalize_operation(db, user, operation.id, expected_version=operation.version)
    db.flush()
    nested.rollback()
    db.expire_all()
    parent = db.get(ParentContract, parent.id)
    operation = db.get(Operation, operation.id)
    assert parent.next_transfer_sequence == 1
    assert operation.status == "DRAFT"
    assert operation.transfer_sequence is None
    assert operation.child_contract_number is None
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(
        OperationVersion.operation_id == operation.id
    )) == 0



def test_database_rejects_operation_party_project_mismatches():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    try:
        with Session(engine) as session:
            project = Project(code="PARTY-A", name="Party Project A", status="ACTIVE",
                              timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            other_project = Project(code="PARTY-B", name="Party Project B", status="ACTIVE",
                                    timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            user = User(username="party-integrity-user", password_hash="unused", display_name="Party User",
                        active=True, created_at=now, updated_at=now, version=1)
            operation_type = OperationType(code="PARTY-TEST", name="Party Test", active=True,
                                           system_defined=False, created_at=now, updated_at=now)
            person = Person(first_name="Other", last_name="Project", created_at=now, updated_at=now,
                            version=1, is_active=True)
            role = PartyRole(code="PARTY-TEST-ROLE", name="Test Role", active=True, system_defined=False,
                             created_at=now, updated_at=now)
            session.add_all([project, other_project, user, operation_type, person, role])
            session.flush()
            session.add(ProjectPerson(project_id=other_project.id, person_id=person.id, active=True,
                                      created_at=now, updated_at=now))
            operation = Operation(project_id=project.id, operation_type_id=operation_type.id, status="DRAFT",
                                  current_workflow_state="DRAFT", created_by=user.id, created_at=now,
                                  updated_at=now, version=1, current_version_number=0)
            session.add(operation)
            session.commit()

            session.add(OperationParty(project_id=other_project.id, operation_id=operation.id,
                                       person_id=person.id, role_id=role.id, sequence_no=1,
                                       created_at=now, updated_at=now, version=1))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(OperationParty(project_id=project.id, operation_id=operation.id,
                                       person_id=person.id, role_id=role.id, sequence_no=1,
                                       created_at=now, updated_at=now, version=1))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()



def test_database_rejects_cross_project_operation_appointment_links():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    try:
        with Session(engine) as session:
            project = Project(code="APPT-A", name="Appointment Project A", status="ACTIVE",
                              timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            other_project = Project(code="APPT-B", name="Appointment Project B", status="ACTIVE",
                                    timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            user = User(username="appointment-integrity-user", password_hash="unused",
                        display_name="Appointment User", active=True, created_at=now, updated_at=now, version=1)
            operation_type = OperationType(code="APPT-OP", name="Appointment Operation", active=True,
                                           system_defined=False, created_at=now, updated_at=now)
            appointment_type = AppointmentType(code="APPT-TYPE", name="Appointment Type",
                                               attendance_behavior="ATTENDANCE_ONLY",
                                               default_duration_minutes=30, active=True,
                                               created_at=now, updated_at=now)
            session.add_all([project, other_project, user, operation_type, appointment_type])
            session.flush()
            operation = Operation(project_id=project.id, operation_type_id=operation_type.id,
                                  status="DRAFT", current_workflow_state="DRAFT", created_by=user.id,
                                  created_at=now, updated_at=now, version=1, current_version_number=0)
            appointment_a = Appointment(project_id=project.id, appointment_type_id=appointment_type.id,
                                        start_at=now, end_at=now + timedelta(minutes=30), status="RESERVED",
                                        created_by=user.id, created_at=now, updated_at=now, version=1)
            appointment_b = Appointment(project_id=other_project.id, appointment_type_id=appointment_type.id,
                                        start_at=now, end_at=now + timedelta(minutes=30), status="RESERVED",
                                        created_by=user.id, created_at=now, updated_at=now, version=1)
            session.add_all([operation, appointment_a, appointment_b])
            session.commit()

            session.add(OperationAppointment(project_id=project.id, appointment_id=appointment_a.id,
                                             operation_id=operation.id, created_at=now))
            session.commit()

            session.add(OperationAppointment(project_id=other_project.id, appointment_id=appointment_b.id,
                                             operation_id=operation.id, created_at=now))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(OperationAppointment(project_id=project.id, appointment_id=appointment_b.id,
                                             operation_id=operation.id, created_at=now))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
