"""Create parent contract transfer-chain tables."""
from alembic import op
import sqlalchemy as sa

revision = "0007_parent_contracts"
down_revision = "0006_remove_operation_appointment_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("contract_code", sa.String(length=2), nullable=True))
    op.create_index("uq_projects_contract_code", "projects", ["contract_code"], unique=True)
    with op.batch_alter_table("projects") as batch:
        batch.create_check_constraint("ck_projects_contract_code_format", "contract_code IS NULL OR contract_code GLOB '[1-9][0-9]'")
    op.create_table(
        "parent_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contract_number", sa.String(length=6), nullable=False, unique=True),
        sa.Column("suffix", sa.String(length=4), nullable=False),
        sa.Column("initial_person_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("project_id", "suffix", name="uq_parent_contract_project_suffix"),
        sa.CheckConstraint("contract_number GLOB '[1-9][0-9][0-9][0-9][0-9][0-9]'", name="ck_parent_contract_number_format"),
        sa.CheckConstraint("suffix GLOB '[0-9][0-9][0-9][0-9]'", name="ck_parent_contract_suffix_format"),
    )
    with op.batch_alter_table("operations") as batch:
        batch.add_column(sa.Column("parent_contract_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("transfer_sequence", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("child_contract_number", sa.String(length=32), nullable=True))
        batch.create_foreign_key("fk_operations_parent_contract", "parent_contracts", ["parent_contract_id"], ["id"], ondelete="RESTRICT")
        batch.create_unique_constraint("uq_operations_child_contract_number", ["child_contract_number"])
        batch.create_unique_constraint("uq_operations_parent_transfer_sequence", ["parent_contract_id", "transfer_sequence"])


def downgrade() -> None:
    with op.batch_alter_table("operations") as batch:
        batch.drop_constraint("uq_operations_parent_transfer_sequence", type_="unique")
        batch.drop_constraint("uq_operations_child_contract_number", type_="unique")
        batch.drop_constraint("fk_operations_parent_contract", type_="foreignkey")
        batch.drop_column("child_contract_number")
        batch.drop_column("transfer_sequence")
        batch.drop_column("parent_contract_id")
    op.drop_table("parent_contracts")
    op.drop_index("uq_projects_contract_code", table_name="projects")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_contract_code_format", type_="check")
    op.drop_column("projects", "contract_code")
