"""Add immutable workflow activity events for period reports."""
from alembic import op
import sqlalchemy as sa

revision = "0009_workflow_events"
down_revision = "0008_transfer_sequence_counter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.Text()),
    )
    op.create_index("ix_workflow_events_project_time", "workflow_events", ["project_id", "occurred_at"])
    op.create_index("ix_workflow_events_operation_time", "workflow_events", ["operation_id", "occurred_at"])
    op.create_index("ix_workflow_events_actor_time", "workflow_events", ["actor_user_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_events_actor_time", table_name="workflow_events")
    op.drop_index("ix_workflow_events_operation_time", table_name="workflow_events")
    op.drop_index("ix_workflow_events_project_time", table_name="workflow_events")
    op.drop_table("workflow_events")
