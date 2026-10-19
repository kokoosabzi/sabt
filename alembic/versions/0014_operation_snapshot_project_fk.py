"""Bind operation snapshots to their project-scoped source records."""
from alembic import op
import sqlalchemy as sa

revision = "0014_operation_snapshot_project_fk"
down_revision = "0013_operation_appointment_project_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("person_snapshots", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("property_snapshots", sa.Column("project_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE person_snapshots
        SET project_id = (
            SELECT operations.project_id
            FROM operations
            WHERE operations.id = person_snapshots.operation_id
        )
    """))
    bind.execute(sa.text("""
        UPDATE property_snapshots
        SET project_id = (
            SELECT operations.project_id
            FROM operations
            WHERE operations.id = property_snapshots.operation_id
        )
    """))

    invalid_person_snapshots = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM person_snapshots AS snapshots
        WHERE snapshots.project_id IS NULL
           OR (snapshots.person_id IS NOT NULL AND NOT EXISTS (
               SELECT 1 FROM project_persons AS memberships
               WHERE memberships.project_id = snapshots.project_id
                 AND memberships.person_id = snapshots.person_id
           ))
           OR (snapshots.party_id IS NOT NULL AND NOT EXISTS (
               SELECT 1 FROM operation_parties AS parties
               WHERE parties.project_id = snapshots.project_id
                 AND parties.operation_id = snapshots.operation_id
                 AND parties.id = snapshots.party_id
           ))
           OR (snapshots.party_id IS NOT NULL AND snapshots.person_id IS NOT NULL AND NOT EXISTS (
               SELECT 1 FROM operation_parties AS parties
               WHERE parties.project_id = snapshots.project_id
                 AND parties.operation_id = snapshots.operation_id
                 AND parties.id = snapshots.party_id
                 AND parties.person_id = snapshots.person_id
           ))
    """)).scalar_one()
    invalid_property_snapshots = bind.execute(sa.text("""
        SELECT COUNT(*)
        FROM property_snapshots AS snapshots
        WHERE snapshots.project_id IS NULL
           OR (snapshots.property_id IS NOT NULL AND NOT EXISTS (
               SELECT 1 FROM project_properties AS memberships
               WHERE memberships.project_id = snapshots.project_id
                 AND memberships.property_id = snapshots.property_id
           ))
           OR (snapshots.property_id IS NOT NULL AND NOT EXISTS (
               SELECT 1 FROM operations
               WHERE operations.project_id = snapshots.project_id
                 AND operations.id = snapshots.operation_id
                 AND operations.property_id = snapshots.property_id
           ))
    """)).scalar_one()
    if invalid_person_snapshots or invalid_property_snapshots:
        raise RuntimeError(
            "Cannot enforce snapshot project integrity: "
            f"{invalid_person_snapshots} person snapshot(s) and "
            f"{invalid_property_snapshots} property snapshot(s) are inconsistent."
        )

    with op.batch_alter_table("operations") as batch:
        batch.create_unique_constraint(
            "uq_operations_project_id_property", ["project_id", "id", "property_id"]
        )
    with op.batch_alter_table("operation_parties") as batch:
        batch.create_unique_constraint(
            "uq_operation_parties_project_operation_id", ["project_id", "operation_id", "id"]
        )
        batch.create_unique_constraint(
            "uq_operation_parties_project_operation_id_person",
            ["project_id", "operation_id", "id", "person_id"],
        )

    with op.batch_alter_table("person_snapshots") as batch:
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_person_snapshots_project_operation", "operations",
            ["project_id", "operation_id"], ["project_id", "id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_person_snapshots_project_person", "project_persons",
            ["project_id", "person_id"], ["project_id", "person_id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_person_snapshots_project_party", "operation_parties",
            ["project_id", "operation_id", "party_id"],
            ["project_id", "operation_id", "id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_person_snapshots_party_person_match", "operation_parties",
            ["project_id", "operation_id", "party_id", "person_id"],
            ["project_id", "operation_id", "id", "person_id"], ondelete="RESTRICT",
        )

    with op.batch_alter_table("property_snapshots") as batch:
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_property_snapshots_project_operation", "operations",
            ["project_id", "operation_id"], ["project_id", "id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_property_snapshots_project_property", "project_properties",
            ["project_id", "property_id"], ["project_id", "property_id"], ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_property_snapshots_operation_property_match", "operations",
            ["project_id", "operation_id", "property_id"],
            ["project_id", "id", "property_id"], ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("property_snapshots") as batch:
        batch.drop_constraint("fk_property_snapshots_operation_property_match", type_="foreignkey")
        batch.drop_constraint("fk_property_snapshots_project_property", type_="foreignkey")
        batch.drop_constraint("fk_property_snapshots_project_operation", type_="foreignkey")
        batch.drop_column("project_id")

    with op.batch_alter_table("person_snapshots") as batch:
        batch.drop_constraint("fk_person_snapshots_party_person_match", type_="foreignkey")
        batch.drop_constraint("fk_person_snapshots_project_party", type_="foreignkey")
        batch.drop_constraint("fk_person_snapshots_project_person", type_="foreignkey")
        batch.drop_constraint("fk_person_snapshots_project_operation", type_="foreignkey")
        batch.drop_column("project_id")

    with op.batch_alter_table("operation_parties") as batch:
        batch.drop_constraint("uq_operation_parties_project_operation_id_person", type_="unique")
        batch.drop_constraint("uq_operation_parties_project_operation_id", type_="unique")

    with op.batch_alter_table("operations") as batch:
        batch.drop_constraint("uq_operations_project_id_property", type_="unique")
