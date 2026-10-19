"""Bind operation parties to the operation and person membership project."""
from alembic import op
import sqlalchemy as sa

revision = "0012_operation_party_project_fk"
down_revision = "0011_workflow_event_project_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operation_parties", sa.Column("project_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE operation_parties
        SET project_id = (
            SELECT operations.project_id
            FROM operations
            WHERE operations.id = operation_parties.operation_id
        )
    """))

    invalid_rows = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM operation_parties AS parties
        WHERE parties.project_id IS NULL
           OR NOT EXISTS (
               SELECT 1
               FROM project_persons AS memberships
               WHERE memberships.project_id = parties.project_id
                 AND memberships.person_id = parties.person_id
           )
    """)).scalar_one()
    if invalid_rows:
        raise RuntimeError(
            "Cannot enforce operation-party project integrity: "
            f"{invalid_rows} existing row(s) have no matching project membership."
        )

    with op.batch_alter_table("operation_parties") as batch:
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_operation_parties_project_operation",
            "operations",
            ["project_id", "operation_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_operation_parties_project_person",
            "project_persons",
            ["project_id", "person_id"],
            ["project_id", "person_id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("operation_parties") as batch:
        batch.drop_constraint("fk_operation_parties_project_person", type_="foreignkey")
        batch.drop_constraint("fk_operation_parties_project_operation", type_="foreignkey")
        batch.drop_column("project_id")
