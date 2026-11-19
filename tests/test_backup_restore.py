import sqlite3
from pathlib import Path

import pytest

from app.backup import BackupError, create_backup, restore_backup


def _create_database(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        connection.execute("INSERT INTO alembic_version(version_num) VALUES ('test-head')")
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO records(value) VALUES (?)", (value,))


def _read_value(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT value FROM records ORDER BY id LIMIT 1").fetchone()[0]


def test_online_backup_captures_committed_wal_data(tmp_path):
    source = tmp_path / "live" / "sabt.db"
    source.parent.mkdir(parents=True)
    connection = sqlite3.connect(source)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        connection.execute("INSERT INTO alembic_version VALUES ('test-head')")
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO records(value) VALUES ('committed in WAL')")
        connection.commit()

        backup = create_backup(source, tmp_path / "backups")
        assert backup.is_file()
        assert _read_value(backup) == "committed in WAL"
    finally:
        connection.close()


def test_restore_replaces_database_and_creates_pre_restore_safety_copy(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "live" / "sabt.db"
    _create_database(source, "from backup")
    _create_database(target, "current live data")
    backup = create_backup(source, tmp_path / "backups")

    safety = restore_backup(
        backup,
        target,
        pid_file=tmp_path / "run" / "server.pid",
        backup_directory=tmp_path / "safety",
    )

    assert safety is not None and safety.is_file()
    assert safety.name.startswith("sabt-pre-restore-")
    assert not Path(f"{target}-wal").exists()
    assert not Path(f"{target}-shm").exists()
    assert _read_value(safety) == "current live data"
    assert _read_value(target) == "from backup"


def test_restore_refuses_to_run_while_server_pid_file_exists(tmp_path):
    source = tmp_path / "source.db"
    target = tmp_path / "live.db"
    pid_file = tmp_path / "run" / "server.pid"
    _create_database(source, "backup")
    _create_database(target, "live")
    backup = create_backup(source, tmp_path / "backups")
    pid_file.parent.mkdir(parents=True)
    pid_file.write_text("12345", encoding="ascii")

    with pytest.raises(BackupError, match="stop.bat"):
        restore_backup(backup, target, pid_file=pid_file)

    assert _read_value(target) == "live"


def test_restore_rejects_non_sabt_or_corrupt_backup(tmp_path):
    source = tmp_path / "not-sabt.db"
    target = tmp_path / "live.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
    _create_database(target, "live")

    with pytest.raises(BackupError, match="مهاجرت‌شده SABT نیست"):
        restore_backup(source, target, pid_file=tmp_path / "no-pid")

    assert _read_value(target) == "live"


def test_backup_names_are_unique_when_created_in_the_same_second(tmp_path):
    source = tmp_path / "source.db"
    _create_database(source, "value")

    first = create_backup(source, tmp_path / "backups")
    second = create_backup(source, tmp_path / "backups")

    assert first != second
    assert first.exists() and second.exists()
