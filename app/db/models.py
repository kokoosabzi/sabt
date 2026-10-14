from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Tehran")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class Person(Base):
    __tablename__ = "persons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    father_name: Mapped[str | None] = mapped_column(String(100))
    national_id: Mapped[str | None] = mapped_column(String(32))
    mobile: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(Text())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_tower: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(32))
    orientation: Mapped[str | None] = mapped_column(String(64))
    unit_number: Mapped[str | None] = mapped_column(String(64))
    unit_code: Mapped[str | None] = mapped_column(String(128))
    plaque_number: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ProjectPerson(Base):
    __tablename__ = "project_persons"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ProjectProperty(Base):
    __tablename__ = "project_properties"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    context_json: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="RESTRICT"), primary_key=True)

class ProjectAccess(Base):
    __tablename__ = "project_access"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class UserRole(Base):
    __tablename__ = "user_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    __table_args__ = (UniqueConstraint("user_id", "role_id", "project_id", name="uq_user_role_scope"),)

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class OperationType(Base):
    __tablename__ = "operation_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    system_defined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ProjectOperationType(Base):
    __tablename__ = "project_operation_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("project_id", "operation_type_id", name="uq_project_operation_type"),)

class PartyRole(Base):
    __tablename__ = "party_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    system_defined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_workflow_state: Mapped[str] = mapped_column(String(64), nullable=False)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    finalized_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class OperationParty(Base):
    __tablename__ = "operation_parties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("party_roles.id", ondelete="RESTRICT"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("operation_id","role_id","sequence_no",name="uq_operation_party_role_seq"),)

class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False, unique=True)
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class OperationVersion(Base):
    __tablename__ = "operation_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_json: Mapped[str] = mapped_column(Text(), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("operation_id","version_number",name="uq_operation_version"),)

class PersonSnapshot(Base):
    __tablename__ = "person_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("operation_parties.id", ondelete="RESTRICT"))
    snapshot_data_json: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)

class PropertySnapshot(Base):
    __tablename__ = "property_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"))
    snapshot_data_json: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DocumentType(Base):
    __tablename__ = "document_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_mime_types: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class OperationTypeRequiredRole(Base):
    __tablename__ = "operation_type_required_roles"
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"), primary_key=True)
    party_role_id: Mapped[int] = mapped_column(ForeignKey("party_roles.id", ondelete="RESTRICT"), primary_key=True)
    min_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_count: Mapped[int | None] = mapped_column(Integer)
    sequence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class OperationTypeRequiredDocument(Base):
    __tablename__ = "operation_type_required_documents"
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"), primary_key=True)
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_types.id", ondelete="RESTRICT"), primary_key=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_count: Mapped[int | None] = mapped_column(Integer)

class OperationTypeWorkflow(Base):
    __tablename__ = "operation_type_workflows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_type_id: Mapped[int] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    state_code: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str | None] = mapped_column(Text())
    __table_args__ = (UniqueConstraint("operation_type_id", "project_id", "state_code", name="uq_operation_type_workflow_state"),)

class NumberingPolicy(Base):
    __tablename__ = "numbering_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    operation_type_id: Mapped[int | None] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"))
    identifier_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    prefix: Mapped[str | None] = mapped_column(String(64))
    sequence_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reset_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="NEVER")
    format_template: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class NumberingState(Base):
    __tablename__ = "numbering_states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numbering_policy_id: Mapped[int] = mapped_column(ForeignKey("numbering_policies.id", ondelete="RESTRICT"), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(200), nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (UniqueConstraint("numbering_policy_id", "scope_key", name="uq_numbering_state_scope"),)

class ContractNumberPolicy(Base):
    __tablename__ = "contract_number_policies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    operation_type_id: Mapped[int | None] = mapped_column(ForeignKey("operation_types.id", ondelete="RESTRICT"))
    uniqueness_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class AppointmentType(Base):
    __tablename__ = "appointment_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    attendance_behavior: Mapped[str] = mapped_column(String(64), nullable=False)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    appointment_type_id: Mapped[int] = mapped_column(ForeignKey("appointment_types.id", ondelete="RESTRICT"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class OperationAppointment(Base):
    __tablename__ = "operation_appointments"
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("appointment_id", "operation_id", name="uq_appointment_operation_link"),)
