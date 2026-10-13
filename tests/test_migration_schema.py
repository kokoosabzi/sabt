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
            migrated_columns = {column["name"] for column in inspector.get_columns(table_name)}
            orm_columns = set(Base.metadata.tables[table_name].columns.keys())
            assert migrated_columns == orm_columns, (
                f"{table_name}: ORM-only columns {sorted(orm_columns - migrated_columns)}; "
                f"migration-only columns {sorted(migrated_columns - orm_columns)}"
            )
    finally:
        engine.dispose()
