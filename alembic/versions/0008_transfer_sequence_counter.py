"""Add atomic transfer sequence counter to ParentContract."""
from alembic import op
import sqlalchemy as sa

revision = "0008_transfer_sequence_counter"
down_revision = "0007_parent_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parent_contracts",
        sa.Column("next_transfer_sequence", sa.Integer(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("parent_contracts") as batch:
        batch.create_check_constraint(
            "ck_parent_contract_next_transfer_sequence_positive",
            "next_transfer_sequence >= 1",
        )


def downgrade() -> None:
    with op.batch_alter_table("parent_contracts") as batch:
        batch.drop_constraint("ck_parent_contract_next_transfer_sequence_positive", type_="check")
        batch.drop_column("next_transfer_sequence")
