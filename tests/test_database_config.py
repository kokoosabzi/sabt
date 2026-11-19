from pathlib import Path

from sqlalchemy.engine import make_url

from app.db.config import DEFAULT_DATABASE_URL, get_database_url


def test_database_url_keeps_repository_relative_default(monkeypatch):
    monkeypatch.delenv("SABT_DATA_DIR", raising=False)

    assert get_database_url() == DEFAULT_DATABASE_URL


def test_database_url_uses_and_creates_configured_data_directory(tmp_path, monkeypatch):
    data_directory = tmp_path / "SABT user data"
    monkeypatch.setenv("SABT_DATA_DIR", str(data_directory))

    url = make_url(get_database_url())

    assert url.get_backend_name() == "sqlite"
    assert Path(url.database) == (data_directory / "sabt.db").resolve()
    assert data_directory.is_dir()
