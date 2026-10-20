"""Bind project-specific workflow and numbering policies to configured operation types."""
from alembic import op
import sqlalchemy as sa

revision = "0017_project_scoped_policy_fks"
down_revision = "0016_contract_project_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    checks = {
        "operation_type_workflows": """SELECT COUNT(*) FROM operation_type_workflows AS policy
            WHERE policy.project_id IS NOT NULL AND policy.operation_type_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM project_operation_types AS configured
                WHERE configured.project_id = policy.project_id
                  AND configured.operation_type_id = policy.operation_type_id)""",
        "numbering_policies": """SELECT COUNT(*) FROM numbering_policies AS policy
            WHERE policy.project_id IS NOT NULL AND policy.operation_type_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM project_operation_types AS configured
                WHERE configured.project_id = policy.project_id
                  AND configured.operation_type_id = policy.operation_type_id)""",
        "contract_number_policies": """SELECT COUNT(*) FROM contract_number_policies AS policy
            WHERE policy.project_id IS NOT NULL AND policy.operation_type_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM project_operation_types AS configured
                WHERE configured.project_id = policy.project_id
                  AND configured.operation_type_id = policy.operation_type_id)""",
    }
    invalid = {
        table: bind.execute(sa.text(query)).scalar_one()
        for table, query in checks.items()
    }
    invalid = {table: count for table, count in invalid.items() if count}
    if invalid:
        details = ", ".join(f"{table}={count}" for table, count in sorted(invalid.items()))
        raise RuntimeError(
            "Cannot enforce project-scoped policy integrity; project-specific "
            f"policies reference operation types not configured for their project ({details})."
        )

    constraints = (
        ("operation_type_workflows", "fk_operation_type_workflows_project_operation_type"),
        ("numbering_policies", "fk_numbering_policies_project_operation_type"),
        ("contract_number_policies", "fk_contract_number_policies_project_operation_type"),
    )
    for table, name in constraints:
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(
                name,
                "project_operation_types",
                ["project_id", "operation_type_id"],
                ["project_id", "operation_type_id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    constraints = (
        ("contract_number_policies", "fk_contract_number_policies_project_operation_type"),
        ("numbering_policies", "fk_numbering_policies_project_operation_type"),
        ("operation_type_workflows", "fk_operation_type_workflows_project_operation_type"),
    )
    for table, name in constraints:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="foreignkey")
