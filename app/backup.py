"""Safe SQLite backup and offline restore utilities for SABT.

Create a consistent online backup:
    python -m app.backup create

Restore a backup only after stopping SABT:
    python -m app.backup restore <backup-file> --confirm
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app.db.config import get_database_url


class BackupError(RuntimeError):
    """A safe, user-displayable backup/restore refusal."""


def get_database_path() -> Path:
    url = make_url(get_database_url())
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise BackupError("این ابزار فقط از دیتابیس SQLite فایل‌محور پشتیبانی می‌کند.")
    path = Path(url.database).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def default_backup_directory(database_path: Path) -> Path:
    configured = os.environ.get("SABT_BACKUP_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    data_directory = os.environ.get("SABT_DATA_DIR")
    if data_directory:
        return Path(data_directory).expanduser().resolve().parent / "backups"
    return database_path.parent / "backups"


def default_server_pid_file(database_path: Path) -> Path:
    configured = os.environ.get("SABT_RUN_DIR")
    if configured:
        return Path(configured).expanduser().resolve() / "server.pid"
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "SABT" / "run" / "server.pid"
    return database_path.parent / "run" / "server.pid"


def _validate_sqlite_database(path: Path) -> None:
    if not path.is_file():
        raise BackupError(f"فایل دیتابیس پیدا نشد: {path}")
    try:
        with closing(sqlite3.connect(str(path), timeout=30)) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise BackupError(f"بررسی سلامت SQLite ناموفق بود: {path}")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "alembic_version" not in tables:
                raise BackupError("فایل انتخاب‌شده دیتابیس مهاجرت‌شده SABT نیست.")
            version = connection.execute(
                "SELECT version_num FROM alembic_version LIMIT 1"
            ).fetchone()
            if not version or not version[0]:
                raise BackupError("نسخه مهاجرت دیتابیس در فایل موجود نیست.")
    except sqlite3.DatabaseError as exc:
        raise BackupError(f"فایل SQLite معتبر نیست: {path}") from exc


def _sqlite_backup(source: Path, destination: Path) -> None:
    with closing(sqlite3.connect(str(source), timeout=30)) as source_connection:
        with closing(sqlite3.connect(str(destination), timeout=30)) as destination_connection:
            source_connection.backup(destination_connection)
            destination_connection.commit()


def _temporary_database_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".sabt-", suffix=".tmp", dir=directory)
    os.close(descriptor)
    return Path(name)


def create_backup(
    database_path: Path,
    backup_directory: Path | None = None,
    *,
    prefix: str = "sabt",
) -> Path:
    source = database_path.expanduser().resolve()
    _validate_sqlite_database(source)
    destination_directory = (
        backup_directory.expanduser().resolve()
        if backup_directory
        else default_backup_directory(source)
    )
    destination_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final_path = destination_directory / f"{prefix}-{timestamp}.db"
    suffix = 1
    while final_path.exists():
        final_path = destination_directory / f"{prefix}-{timestamp}-{suffix:03d}.db"
        suffix += 1

    temporary = _temporary_database_path(destination_directory)
    try:
        _sqlite_backup(source, temporary)
        _validate_sqlite_database(temporary)
        os.replace(temporary, final_path)
        return final_path
    finally:
        temporary.unlink(missing_ok=True)


def restore_backup(
    backup_path: Path,
    database_path: Path,
    *,
    pid_file: Path | None = None,
    backup_directory: Path | None = None,
) -> Path | None:
    source = backup_path.expanduser().resolve()
    target = database_path.expanduser().resolve()
    if source == target:
        raise BackupError("فایل پشتیبان و دیتابیس مقصد نمی‌توانند یک فایل باشند.")
    effective_pid_file = pid_file or default_server_pid_file(target)
    if effective_pid_file.exists():
        raise BackupError(
            "فایل PID سرور وجود دارد. ابتدا SABT را با stop.bat متوقف کنید و سپس بازیابی را انجام دهید."
        )
    _validate_sqlite_database(source)
    target.parent.mkdir(parents=True, exist_ok=True)

    temporary = _temporary_database_path(target.parent)
    safety_backup: Path | None = None
    try:
        _sqlite_backup(source, temporary)
        _validate_sqlite_database(temporary)

        if target.exists():
            safety_backup = create_backup(
                target,
                backup_directory or default_backup_directory(target),
                prefix="sabt-pre-restore",
            )

        # A stopped SQLite database may still have WAL/SHM sidecars. The online
        # backup above includes committed WAL content; remove sidecars before
        # replacing the main file so they cannot be replayed against the restore.
        Path(f"{target}-wal").unlink(missing_ok=True)
        Path(f"{target}-shm").unlink(missing_ok=True)
        os.replace(temporary, target)
        return safety_backup
    finally:
        temporary.unlink(missing_ok=True)


def _configure_console_encoding() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(description="Create or restore SABT SQLite backups.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a consistent online backup.")
    create_parser.add_argument("--destination", type=Path, default=None)

    restore_parser = subparsers.add_parser("restore", help="Restore a backup while SABT is stopped.")
    restore_parser.add_argument("backup_file", type=Path)
    restore_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required explicit confirmation before replacing the current database.",
    )
    restore_parser.add_argument("--destination", type=Path, default=None,
                                help="Directory for the automatic pre-restore safety backup.")

    args = parser.parse_args(argv)
    try:
        database_path = get_database_path()
        if args.command == "create":
            result = create_backup(database_path, args.destination)
            print(result)
            return 0

        if not args.confirm:
            raise BackupError("برای جایگزینی دیتابیس باید گزینه --confirm را صریحاً وارد کنید.")
        safety_backup = restore_backup(
            args.backup_file,
            database_path,
            backup_directory=args.destination,
        )
        print("بازیابی دیتابیس با موفقیت انجام شد.")
        if safety_backup:
            print(f"نسخه ایمنی قبل از بازیابی: {safety_backup}")
        print("برای اعمال مهاجرت‌های جدید، start.bat را اجرا کنید.")
        return 0
    except BackupError as exc:
        print(f"عملیات پشتیبان‌گیری/بازیابی انجام نشد: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
