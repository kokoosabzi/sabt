from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contract_code: Mapped[str | None] = mapped_column(String(2), unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    __table_args__ = (
        CheckConstraint("contract_code IS NULL OR contract_code GLOB '[1-9][0-9]'", name="ck_projects_contract_code_format"),
        Index("ix_projects_name", "name"),
    )
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
    __table_args__ = (Index("ix_persons_national_id", "national_id"), Index("ix_persons_mobile", "mobile"))

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
    __table_args__ = (
        Index("ix_properties_unit_number", "unit_number"),
        Index("ix_properties_unit_code", "unit_code"),
        Index("ix_properties_plaque_number", "plaque_number"),
    )

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
    __table_args__ = (Index("ix_sessions_user_id", "user_id"), Index("ix_sessions_expires_at", "expires_at"))

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
    parent_contract_id: Mapped[int | None] = mapped_column(ForeignKey("parent_contracts.id", ondelete="RESTRICT"))
    transfer_sequence: Mapped[int | None] = mapped_column(Integer)
    child_contract_number: Mapped[str | None] = mapped_column(String(32))
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_operations_project_id_id"),
        UniqueConstraint("project_id", "id", "property_id", name="uq_operations_project_id_property"),
        UniqueConstraint("child_contract_number", name="uq_operations_child_contract_number"),
        UniqueConstraint("parent_contract_id", "transfer_sequence", name="uq_operations_parent_transfer_sequence"),
        ForeignKeyConstraint(["project_id", "operation_type_id"],
                             ["project_operation_types.project_id", "project_operation_types.operation_type_id"],
                             ondelete="RESTRICT", name="fk_operations_project_operation_type"),
        # A globally valid property/parent ID must also belong to this operation's project.
        ForeignKeyConstraint(["project_id", "property_id"],
                             ["project_properties.project_id", "project_properties.property_id"],
                             ondelete="RESTRICT", name="fk_operations_project_property"),
        ForeignKeyConstraint(["project_id", "parent_contract_id"],
                             ["parent_contracts.project_id", "parent_contracts.id"],
                             ondelete="RESTRICT", name="fk_operations_project_parent_contract"),
        Index("ix_operations_project_status_created", "project_id", "status", "created_at"),
    )

class OperationParty(Base):
    __tablename__ = "operation_parties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("party_roles.id", ondelete="RESTRICT"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        UniqueConstraint("operation_id", "role_id", "sequence_no", name="uq_operation_party_role_seq"),
        UniqueConstraint("project_id", "operation_id", "id", name="uq_operation_parties_project_operation_id"),
        UniqueConstraint("project_id", "operation_id", "id", "person_id", name="uq_operation_parties_project_operation_id_person"),
        ForeignKeyConstraint(
            ["project_id", "operation_id"],
            ["operations.project_id", "operations.id"],
            ondelete="RESTRICT",
            name="fk_operation_parties_project_operation",
        ),
        ForeignKeyConstraint(
            ["project_id", "person_id"],
            ["project_persons.project_id", "project_persons.person_id"],
            ondelete="RESTRICT",
            name="fk_operation_parties_project_person",
        ),
    )

class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False, unique=True)
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "operation_id"], ["operations.project_id", "operations.id"],
                             ondelete="RESTRICT", name="fk_contracts_project_operation"),
        ForeignKeyConstraint(["project_id", "property_id"], ["project_properties.project_id", "project_properties.property_id"],
                             ondelete="RESTRICT", name="fk_contracts_project_property"),
        ForeignKeyConstraint(["project_id", "operation_id", "property_id"],
                             ["operations.project_id", "operations.id", "operations.property_id"],
                             ondelete="RESTRICT", name="fk_contracts_operation_property_match"),
        Index("ix_contracts_contract_number", "contract_number"),
        Index("ix_contracts_registration_number", "registration_number"),
    )

class ParentContract(Base):
    """Stable six-digit business root for a member's transfer history."""
    __tablename__ = "parent_contracts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    contract_number: Mapped[str] = mapped_column(String(6), unique=True, nullable=False)
    suffix: Mapped[str] = mapped_column(String(4), nullable=False)
    initial_person_id: Mapped[int] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    next_transfer_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __table_args__ = (
        CheckConstraint("next_transfer_sequence >= 1", name="ck_parent_contract_next_transfer_sequence_positive"),
        UniqueConstraint("project_id", "suffix", name="uq_parent_contract_project_suffix"),
        UniqueConstraint("project_id", "id", name="uq_parent_contract_project_id_id"),
        CheckConstraint("contract_number GLOB '[1-9][0-9][0-9][0-9][0-9][0-9]'", name="ck_parent_contract_number_format"),
        CheckConstraint("suffix GLOB '[0-9][0-9][0-9][0-9]'", name="ck_parent_contract_suffix_format"),
        ForeignKeyConstraint(["project_id", "initial_person_id"],
                             ["project_persons.project_id", "project_persons.person_id"],
                             ondelete="RESTRICT", name="fk_parent_contract_initial_person_project"),
        ForeignKeyConstraint(["project_id", "property_id"],
                             ["project_properties.project_id", "project_properties.property_id"],
                             ondelete="RESTRICT", name="fk_parent_contract_property_project"),
    )


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
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("operation_parties.id", ondelete="RESTRICT"))
    snapshot_data_json: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "operation_id"], ["operations.project_id", "operations.id"],
                             ondelete="RESTRICT", name="fk_person_snapshots_project_operation"),
        ForeignKeyConstraint(["project_id", "person_id"], ["project_persons.project_id", "project_persons.person_id"],
                             ondelete="RESTRICT", name="fk_person_snapshots_project_person"),
        ForeignKeyConstraint(["project_id", "operation_id", "party_id"],
                             ["operation_parties.project_id", "operation_parties.operation_id", "operation_parties.id"],
                             ondelete="RESTRICT", name="fk_person_snapshots_project_party"),
        ForeignKeyConstraint(["project_id", "operation_id", "party_id", "person_id"],
                             ["operation_parties.project_id", "operation_parties.operation_id", "operation_parties.id", "operation_parties.person_id"],
                             ondelete="RESTRICT", name="fk_person_snapshots_party_person_match"),
    )

class PropertySnapshot(Base):
    __tablename__ = "property_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id", ondelete="RESTRICT"))
    snapshot_data_json: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "operation_id"], ["operations.project_id", "operations.id"],
                             ondelete="RESTRICT", name="fk_property_snapshots_project_operation"),
        ForeignKeyConstraint(["project_id", "property_id"], ["project_properties.project_id", "project_properties.property_id"],
                             ondelete="RESTRICT", name="fk_property_snapshots_project_property"),
        ForeignKeyConstraint(["project_id", "operation_id", "property_id"],
                             ["operations.project_id", "operations.id", "operations.property_id"],
                             ondelete="RESTRICT", name="fk_property_snapshots_operation_property_match"),
    )


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
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_appointments_project_id_id"),
        Index("ix_appointments_project_start", "project_id", "start_at"),
        Index("ix_appointments_status", "status"),
    )

class OperationAppointment(Base):
    __tablename__ = "operation_appointments"
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("appointment_id", "operation_id", name="uq_appointment_operation_link"),
        ForeignKeyConstraint(
            ["project_id", "appointment_id"],
            ["appointments.project_id", "appointments.id"],
            ondelete="RESTRICT",
            name="fk_operation_appointments_project_appointment",
        ),
        ForeignKeyConstraint(
            ["project_id", "operation_id"],
            ["operations.project_id", "operations.id"],
            ondelete="RESTRICT",
            name="fk_operation_appointments_project_operation",
        ),
    )


class WorkflowEvent(Base):
    """Immutable audit record for a real workflow/activity event."""
    __tablename__ = "workflow_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text())
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "operation_id"],
            ["operations.project_id", "operations.id"],
            ondelete="RESTRICT",
            name="fk_workflow_events_project_operation",
        ),
        Index("ix_workflow_events_project_time", "project_id", "occurred_at"),
        Index("ix_workflow_events_operation_time", "operation_id", "occurred_at"),
        Index("ix_workflow_events_actor_time", "actor_user_id", "occurred_at"),
    )
