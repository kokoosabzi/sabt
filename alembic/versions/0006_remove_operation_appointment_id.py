"""remove redundant direct appointment link from operations

The operation_appointments junction is the single source of truth for the
many-to-many appointment/operation relationship.
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_remove_operation_appointment_id"
down_revision = "0005_appointments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("operations") as batch_op:
        batch_op.drop_column("appointment_id")


def downgrade() -> None:
    with op.batch_alter_table("operations") as batch_op:
        batch_op.add_column(sa.Column("appointment_id", sa.Integer(), nullable=True))
