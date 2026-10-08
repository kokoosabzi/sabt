"""core operation and contract domain"""
from alembic import op
import sqlalchemy as sa

revision = "0004_operation_core"
down_revision = "0003_auth_sessions"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("operation_types",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("system_defined", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retired_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("project_operation_types",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("config_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("project_id","operation_type_id",name="uq_project_operation_type"))
    op.create_table("party_roles",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("system_defined", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retired_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("document_types",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("allowed_mime_types", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("operation_type_required_roles",
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("party_role_id", sa.Integer(), sa.ForeignKey("party_roles.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("min_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_count", sa.Integer()), sa.Column("sequence_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("operation_type_required_documents",
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("document_type_id", sa.Integer(), sa.ForeignKey("document_types.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("min_count", sa.Integer(), nullable=False, server_default="1"), sa.Column("max_count", sa.Integer()))
    op.create_table("operation_type_workflows",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT")), sa.Column("state_code", sa.String(64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("config_json", sa.Text()),
        sa.UniqueConstraint("operation_type_id","project_id","state_code",name="uq_operation_type_workflow_state"))
    op.create_table("numbering_policies",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT")),
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT")), sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False), sa.Column("prefix", sa.String(64)), sa.Column("sequence_width", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reset_policy", sa.String(32), nullable=False, server_default="NEVER"), sa.Column("format_template", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("numbering_states",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("numbering_policy_id", sa.Integer(), sa.ForeignKey("numbering_policies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scope_key", sa.String(200), nullable=False), sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("numbering_policy_id","scope_key",name="uq_numbering_state_scope"))
    op.create_table("contract_number_policies",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT")),
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT")), sa.Column("uniqueness_scope", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("operations",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_type_id", sa.Integer(), sa.ForeignKey("operation_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("appointment_id", sa.Integer()),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("current_workflow_state", sa.String(64), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="RESTRICT")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("finalized_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_operations_project_status_created","operations",["project_id","status","created_at"])
    op.create_table("operation_parties",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False), sa.Column("role_id", sa.Integer(), sa.ForeignKey("party_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False, server_default="1"), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("operation_id","role_id","sequence_no",name="uq_operation_party_role_seq"))
    op.create_table("contracts",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("contract_number", sa.String(100), nullable=False), sa.Column("registration_number", sa.String(100)), sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_index("ix_contracts_contract_number","contracts",["contract_number"])
    op.create_index("ix_contracts_registration_number","contracts",["registration_number"])
    op.create_table("operation_versions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("reason", sa.Text()), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("finalized_at", sa.DateTime(timezone=True)), sa.Column("snapshot_json", sa.Text(), nullable=False), sa.Column("hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("operation_id","version_number",name="uq_operation_version"))
    op.create_table("person_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="RESTRICT")), sa.Column("party_id", sa.Integer(), sa.ForeignKey("operation_parties.id", ondelete="RESTRICT")),
        sa.Column("snapshot_data_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("snapshot_hash", sa.String(64), nullable=False))
    op.create_table("property_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="RESTRICT")), sa.Column("snapshot_data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("snapshot_hash", sa.String(64), nullable=False))

def downgrade() -> None:
    for t in ["property_snapshots","person_snapshots","operation_versions","contracts","operation_parties","operations","contract_number_policies","numbering_states","numbering_policies","operation_type_workflows","operation_type_required_documents","operation_type_required_roles","document_types","party_roles","project_operation_types","operation_types"]:
        op.drop_table(t)
