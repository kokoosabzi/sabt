"""Require appointment-operation links to stay within one project."""
from alembic import op
import sqlalchemy as sa

revision = "0013_operation_appointment_project_fk"
down_revision = "0012_operation_party_project_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("appointments") as batch:
        batch.create_unique_constraint(
            "uq_appointments_project_id_id", ["project_id", "id"]
        )

    op.add_column("operation_appointments", sa.Column("project_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE operation_appointments
        SET project_id = (
            SELECT operations.project_id
            FROM operations
            WHERE operations.id = operation_appointments.operation_id
        )
    """))

    invalid_rows = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM operation_appointments AS links
        JOIN operations ON operations.id = links.operation_id
        JOIN appointments ON appointments.id = links.appointment_id
        WHERE operations.project_id != appointments.project_id
           OR links.project_id IS NULL
    """)).scalar_one()
    if invalid_rows:
        raise RuntimeError(
            "Cannot enforce appointment-operation project integrity: "
            f"{invalid_rows} existing link(s) connect different projects."
        )

    with op.batch_alter_table("operation_appointments") as batch:
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_operation_appointments_project_appointment",
            "appointments",
            ["project_id", "appointment_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_operation_appointments_project_operation",
            "operations",
            ["project_id", "operation_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("operation_appointments") as batch:
        batch.drop_constraint("fk_operation_appointments_project_operation", type_="foreignkey")
        batch.drop_constraint("fk_operation_appointments_project_appointment", type_="foreignkey")
        batch.drop_column("project_id")

    with op.batch_alter_table("appointments") as batch:
        batch.drop_constraint("uq_appointments_project_id_id", type_="unique")
