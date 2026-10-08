"""foundation schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Tehran"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    op.create_table("persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("father_name", sa.String(100)),
        sa.Column("national_id", sa.String(32)),
        sa.Column("mobile", sa.String(32)),
        sa.Column("address", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_persons_national_id", "persons", ["national_id"])
    op.create_index("ix_persons_mobile", "persons", ["mobile"])

    op.create_table("properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("block_tower", sa.String(100)),
        sa.Column("floor", sa.String(32)),
        sa.Column("orientation", sa.String(64)),
        sa.Column("unit_number", sa.String(64)),
        sa.Column("unit_code", sa.String(128)),
        sa.Column("plaque_number", sa.String(64)),
        sa.Column("address", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_properties_unit_number", "properties", ["unit_number"])
    op.create_index("ix_properties_unit_code", "properties", ["unit_code"])
    op.create_index("ix_properties_plaque_number", "properties", ["plaque_number"])

    op.create_table("project_persons",
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "person_id"),
    )

    op.create_table("project_properties",
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("context_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "property_id"),
    )


def downgrade() -> None:
    op.drop_table("project_properties")
    op.drop_table("project_persons")
    op.drop_index("ix_properties_plaque_number", table_name="properties")
    op.drop_index("ix_properties_unit_code", table_name="properties")
    op.drop_index("ix_properties_unit_number", table_name="properties")
    op.drop_table("properties")
    op.drop_index("ix_persons_mobile", table_name="persons")
    op.drop_index("ix_persons_national_id", table_name="persons")
    op.drop_table("persons")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")