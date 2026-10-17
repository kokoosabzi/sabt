from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db.base import Base
from app.db import models  # noqa: F401


def test_migrated_schema_contains_all_orm_tables_and_columns(tmp_path):
    database_path = tmp_path / "migration-parity.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        inspector = inspect(engine)
        migrated_tables = set(inspector.get_table_names()) - {"alembic_version"}
        orm_tables = set(Base.metadata.tables)

        assert migrated_tables == orm_tables, (
            f"ORM-only tables: {sorted(orm_tables - migrated_tables)}; "
            f"migration-only tables: {sorted(migrated_tables - orm_tables)}"
        )

        for table_name in sorted(orm_tables):
            migrated_column_info = {
                column["name"]: column for column in inspector.get_columns(table_name)
            }
            orm_column_info = {
                column.name: column for column in Base.metadata.tables[table_name].columns
            }
            migrated_columns = set(migrated_column_info)
            orm_columns = set(orm_column_info)
            assert migrated_columns == orm_columns, (
                f"{table_name}: ORM-only columns {sorted(orm_columns - migrated_columns)}; "
                f"migration-only columns {sorted(migrated_columns - orm_columns)}"
            )

            # Column presence alone is not enough: a nullable column can silently
            # weaken required-field invariants when migrations drift from models.
            for column_name in sorted(orm_columns):
                migrated_nullable = bool(migrated_column_info[column_name]["nullable"])
                orm_nullable = bool(orm_column_info[column_name].nullable)
                assert migrated_nullable == orm_nullable, (
                    f"{table_name}.{column_name}: ORM nullable={orm_nullable}, "
                    f"migrated nullable={migrated_nullable}"
                )

            orm_foreign_keys = set()
            for constraint in Base.metadata.tables[table_name].foreign_key_constraints:
                elements = list(constraint.elements)
                orm_foreign_keys.add((
                    tuple(element.parent.name for element in elements),
                    elements[0].column.table.name,
                    tuple(element.column.name for element in elements),
                    (elements[0].ondelete or "").upper(),
                ))

            migrated_foreign_keys = set()
            for foreign_key in inspector.get_foreign_keys(table_name):
                options = foreign_key.get("options") or {}
                migrated_foreign_keys.add((
                    tuple(foreign_key["constrained_columns"]),
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                    (options.get("ondelete") or "").upper(),
                ))

            assert migrated_foreign_keys == orm_foreign_keys, (
                f"{table_name}: ORM-only foreign keys "
                f"{sorted(orm_foreign_keys - migrated_foreign_keys, key=repr)}; "
                f"migration-only foreign keys "
                f"{sorted(migrated_foreign_keys - orm_foreign_keys, key=repr)}"
            )
    finally:
        engine.dispose()
