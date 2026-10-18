"""Require workflow events to match their operation's project."""
from alembic import op

revision = "0011_workflow_event_project_fk"
down_revision = "0010_project_scoped_fks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("operations") as batch:
        batch.create_unique_constraint(
            "uq_operations_project_id_id", ["project_id", "id"]
        )

    with op.batch_alter_table("workflow_events") as batch:
        batch.create_foreign_key(
            "fk_workflow_events_project_operation",
            "operations",
            ["project_id", "operation_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("workflow_events") as batch:
        batch.drop_constraint(
            "fk_workflow_events_project_operation", type_="foreignkey"
        )

    with op.batch_alter_table("operations") as batch:
        batch.drop_constraint("uq_operations_project_id_id", type_="unique")
