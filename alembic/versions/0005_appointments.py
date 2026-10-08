"""appointment core tables required by operation linkage"""
from alembic import op
import sqlalchemy as sa

revision = "0005_appointments"
down_revision = "0004_operation_core"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("appointment_types",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("attendance_behavior", sa.String(64), nullable=False), sa.Column("default_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("appointments",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("appointment_type_id", sa.Integer(), sa.ForeignKey("appointment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_index("ix_appointments_project_start","appointments",["project_id","start_at"])
    op.create_index("ix_appointments_status","appointments",["status"])
    op.create_table("operation_appointments",
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("operation_id", sa.Integer(), sa.ForeignKey("operations.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("appointment_id","operation_id",name="uq_appointment_operation_link"))

def downgrade() -> None:
    op.drop_table("operation_appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_project_start", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("appointment_types")
