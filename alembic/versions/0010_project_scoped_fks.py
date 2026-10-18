"""Enforce project-scoped property and parent-contract references."""
from alembic import op
import sqlalchemy as sa

revision = "0010_project_scoped_fks"
down_revision = "0009_workflow_event_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the existing scalar FKs for clear entity existence semantics, while
    # adding composite FKs so IDs cannot be paired with a different project.
    with op.batch_alter_table("parent_contracts") as batch:
        batch.create_unique_constraint(
            "uq_parent_contract_project_id_id", ["project_id", "id"]
        )
        batch.create_foreign_key(
            "fk_parent_contract_initial_person_project",
            "project_persons",
            ["project_id", "initial_person_id"],
            ["project_id", "person_id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_parent_contract_property_project",
            "project_properties",
            ["project_id", "property_id"],
            ["project_id", "property_id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("operations") as batch:
        batch.create_foreign_key(
            "fk_operations_project_property",
            "project_properties",
            ["project_id", "property_id"],
            ["project_id", "property_id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_operations_project_parent_contract",
            "parent_contracts",
            ["project_id", "parent_contract_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("operations") as batch:
        batch.drop_constraint("fk_operations_project_parent_contract", type_="foreignkey")
        batch.drop_constraint("fk_operations_project_property", type_="foreignkey")

    with op.batch_alter_table("parent_contracts") as batch:
        batch.drop_constraint("fk_parent_contract_property_project", type_="foreignkey")
        batch.drop_constraint("fk_parent_contract_initial_person_project", type_="foreignkey")
        batch.drop_constraint("uq_parent_contract_project_id_id", type_="unique")
