"""security and access foundation"""
from alembic import op
import sqlalchemy as sa

revision = "0002_security_foundation"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(100), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_login_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("permissions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(150), nullable=False, unique=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text()))
    op.create_table("role_permissions", sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True), sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="RESTRICT"), primary_key=True))
    op.create_table("project_access", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), primary_key=True), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("granted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")), sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table("user_roles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False), sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT")), sa.UniqueConstraint("user_id", "role_id", "project_id", name="uq_user_role_scope"))

def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("project_access")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")