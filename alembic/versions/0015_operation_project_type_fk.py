"""Require each operation type to be configured for its project."""
from alembic import op
import sqlalchemy as sa

revision = "0015_operation_project_type_fk"
down_revision = "0014_operation_snapshot_project_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    invalid_rows = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM operations AS operations
        WHERE NOT EXISTS (
            SELECT 1
            FROM project_operation_types AS configured
            WHERE configured.project_id = operations.project_id
              AND configured.operation_type_id = operations.operation_type_id
        )
    """)).scalar_one()
    if invalid_rows:
        raise RuntimeError(
            "Cannot enforce operation type project integrity: "
            f"{invalid_rows} existing operation(s) lack a project operation-type association."
        )

    with op.batch_alter_table("operations") as batch:
        batch.create_foreign_key(
            "fk_operations_project_operation_type",
            "project_operation_types",
            ["project_id", "operation_type_id"],
            ["project_id", "operation_type_id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("operations") as batch:
        batch.drop_constraint("fk_operations_project_operation_type", type_="foreignkey")
