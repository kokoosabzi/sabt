"""Bind Contract rows to the project and property of their operation."""
from alembic import op
import sqlalchemy as sa

revision = "0016_contract_project_fk"
down_revision = "0015_operation_project_type_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("project_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE contracts
        SET project_id = (
            SELECT operations.project_id
            FROM operations
            WHERE operations.id = contracts.operation_id
        )
    """))

    invalid_rows = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM contracts AS contracts
        LEFT JOIN operations ON operations.id = contracts.operation_id
        WHERE contracts.project_id IS NULL
           OR operations.id IS NULL
           OR operations.project_id != contracts.project_id
           OR operations.property_id IS NOT contracts.property_id
           OR NOT EXISTS (
               SELECT 1
               FROM project_properties AS properties
               WHERE properties.project_id = contracts.project_id
                 AND properties.property_id = contracts.property_id
           )
    """)).scalar_one()
    if invalid_rows:
        raise RuntimeError(
            "Cannot enforce contract project integrity: "
            f"{invalid_rows} existing contract row(s) disagree with their operation or property."
        )

    with op.batch_alter_table("contracts") as batch:
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_contracts_project_operation", "operations",
            ["project_id", "operation_id"], ["project_id", "id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_contracts_project_property", "project_properties",
            ["project_id", "property_id"], ["project_id", "property_id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_contracts_operation_property_match", "operations",
            ["project_id", "operation_id", "property_id"],
            ["project_id", "id", "property_id"], ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("contracts") as batch:
        batch.drop_constraint("fk_contracts_operation_property_match", type_="foreignkey")
        batch.drop_constraint("fk_contracts_project_property", type_="foreignkey")
        batch.drop_constraint("fk_contracts_project_operation", type_="foreignkey")
        batch.drop_column("project_id")
