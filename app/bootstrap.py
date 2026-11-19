"""One-time, interactive creation of the first SABT administrator.

Run after database migrations:
    python -m app.bootstrap

This command never prints or stores the plaintext password and refuses to run
when any user already exists. It does not create a default credential.
"""
from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password
from app.auth.permission_catalog import (
    ADMIN_ROLE_CODE,
    ADMIN_ROLE_DESCRIPTION,
    ADMIN_ROLE_NAME,
    PERMISSION_CATALOG,
)
from app.db.config import get_database_url
from app.db.models import Permission, Role, RolePermission, User, UserRole

ROOT = Path(__file__).resolve().parents[1]
MIN_PASSWORD_LENGTH = 12
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,99}$")


class BootstrapError(RuntimeError):
    """A safe, user-displayable bootstrap refusal."""


def create_initial_admin(
    db: Session, *, username: str, display_name: str, password: str
) -> User:
    """Create the first administrator atomically; never replace an existing user."""
    normalized_username = username.strip().lower()
    normalized_display_name = display_name.strip()
    if not USERNAME_PATTERN.fullmatch(normalized_username):
        raise BootstrapError(
            "نام کاربری باید ۳ تا ۱۰۰ نویسه و شامل حروف لاتین، عدد، نقطه، خط تیره یا زیرخط باشد."
        )
    if not normalized_display_name or len(normalized_display_name) > 200:
        raise BootstrapError("نام نمایشی الزامی و حداکثر ۲۰۰ نویسه است.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BootstrapError(f"گذرواژه باید حداقل {MIN_PASSWORD_LENGTH} نویسه باشد.")

    if db.scalar(select(func.count(User.id))) != 0:
        raise BootstrapError(
            "حداقل یک حساب کاربری وجود دارد؛ راه‌اندازی اولیه فقط روی پایگاه داده بدون کاربر مجاز است."
        )

    now = datetime.now(timezone.utc)
    role = db.scalar(select(Role).where(Role.code == ADMIN_ROLE_CODE))
    if role is None:
        role = Role(
            code=ADMIN_ROLE_CODE,
            name=ADMIN_ROLE_NAME,
            description=ADMIN_ROLE_DESCRIPTION,
            active=True,
        )
        db.add(role)
        db.flush()
    elif not role.active:
        raise BootstrapError("نقش مدیر سیستم موجود اما غیرفعال است؛ ابتدا وضعیت آن را بررسی کنید.")

    permissions: dict[str, Permission] = {}
    for code, name, description in PERMISSION_CATALOG:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, name=name, description=description)
            db.add(permission)
            db.flush()
        permissions[code] = permission

    existing_links = set(
        db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id == role.id)).all()
    )
    for permission in permissions.values():
        if permission.id not in existing_links:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    user = User(
        username=normalized_username,
        password_hash=hash_password(password),
        display_name=normalized_display_name,
        active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, project_id=None))
    db.flush()
    return user


def _verify_migrations(engine) -> None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        raise BootstrapError(
            "پایگاه داده هنوز مهاجرت نشده است. ابتدا دستور alembic upgrade head را اجرا کنید."
        )
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    if current != expected:
        raise BootstrapError(
            f"نسخه پایگاه داده ({current or 'نامشخص'}) با آخرین مهاجرت ({expected}) برابر نیست. ابتدا alembic upgrade head را اجرا کنید."
        )


def main() -> int:
    engine = create_engine(
        get_database_url(),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    try:
        _verify_migrations(engine)
        with Session(engine) as db:
            with db.begin():
                if db.scalar(select(func.count(User.id))) != 0:
                    raise BootstrapError(
                        "این پایگاه داده قبلاً حساب کاربری دارد؛ ایجاد مدیر اولیه مجاز نیست."
                    )
                username = input("نام کاربری مدیر (لاتین): ").strip()
                display_name = input("نام و نام خانوادگی نمایشی: ").strip()
                password = getpass.getpass("گذرواژه مدیر (حداقل ۱۲ نویسه): ")
                confirmation = getpass.getpass("تکرار گذرواژه: ")
                if password != confirmation:
                    raise BootstrapError("تکرار گذرواژه مطابقت ندارد.")
                user = create_initial_admin(
                    db,
                    username=username,
                    display_name=display_name,
                    password=password,
                )
                user_id = user.id
        print(f"مدیر اولیه با موفقیت ایجاد شد. شناسه کاربر: {user_id}")
        print("اکنون می‌توانید با همین نام کاربری و گذرواژه وارد پرتال شوید.")
        return 0
    except BootstrapError as exc:
        print(f"راه‌اندازی انجام نشد: {exc}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
