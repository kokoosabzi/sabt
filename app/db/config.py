"""Shared SQLite location configuration for the SABT runtime and Alembic.

Development keeps the historical repository-relative database unless a data
folder is explicitly supplied. Windows launchers set SABT_DATA_DIR to a stable
per-machine application-data directory; existing databases are never moved.
"""
import os
from pathlib import Path

from sqlalchemy.engine import URL

DEFAULT_DATABASE_URL = "sqlite:///./sabt.db"
DATA_DIRECTORY_ENV = "SABT_DATA_DIR"


def get_database_url() -> str:
    """Return the SQLite URL shared by the application and Alembic."""
    configured_directory = os.environ.get(DATA_DIRECTORY_ENV)
    if not configured_directory:
        return DEFAULT_DATABASE_URL

    data_directory = Path(configured_directory).expanduser().resolve()
    data_directory.mkdir(parents=True, exist_ok=True)
    database_path = data_directory / "sabt.db"
    return URL.create("sqlite", database=str(database_path)).render_as_string(
        hide_password=False
    )
