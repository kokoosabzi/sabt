from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Appointment,
    AppointmentType,
    Operation,
    OperationAppointment,
    OperationType,
    Permission,
    Project,
    ProjectAccess,
    ProjectOperationType,
    ProjectProperty,
    Property,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.operations.service import ValidationError, create_operation


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
    appointment_type = AppointmentType(
        code="CONSULT",
        name="Consultation",
        attendance_behavior="ATTENDANCE_ONLY",
        default_duration_minutes=30,
        active=True,
        created_at=now,
        updated_at=now,
    )
    db.add_all([user, project, other_project, operation_type, property_record, role, permission, appointment_type])
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id),
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
