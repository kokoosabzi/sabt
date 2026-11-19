from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.permission_catalog import ADMIN_ROLE_CODE, PERMISSION_CATALOG
from app.auth.passwords import verify_password
from app.bootstrap import BootstrapError, create_initial_admin, get_bootstrap_status
from app.db.base import Base
from app.db.models import Permission, Role, RolePermission, User, UserRole


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_bootstrap_status_changes_after_first_admin_is_created(db):
    assert get_bootstrap_status(db) == "needs-admin"

    create_initial_admin(
        db,
        username="first.admin",
        display_name="مدیر نخست",
        password="a secure initial password",
    )
    db.commit()

    assert get_bootstrap_status(db) == "configured"


def test_initial_admin_is_created_with_hashed_password_and_full_catalog(db):
    user = create_initial_admin(
        db,
        username="First.Admin",
        display_name="مدیر نخست",
        password="a secure initial password",
    )
    db.commit()

    assert user.username == "first.admin"
    assert user.active is True
    assert user.password_hash != "a secure initial password"
    assert verify_password("a secure initial password", user.password_hash)

    role = db.scalar(select(Role).where(Role.code == ADMIN_ROLE_CODE))
    assert role is not None and role.active
    assignment = db.scalar(select(UserRole).where(UserRole.user_id == user.id))
    assert assignment is not None
    assert assignment.role_id == role.id
    assert assignment.project_id is None

    permission_count = db.scalar(select(func.count(Permission.id)))
    link_count = db.scalar(
        select(func.count(RolePermission.permission_id)).where(
            RolePermission.role_id == role.id
        )
    )
    assert permission_count == len(PERMISSION_CATALOG)
    assert link_count == len(PERMISSION_CATALOG)


def test_bootstrap_refuses_to_create_a_second_user(db):
    create_initial_admin(
        db,
        username="first.admin",
        display_name="مدیر نخست",
        password="a secure initial password",
    )
    db.commit()

    with pytest.raises(BootstrapError, match="فقط روی پایگاه داده بدون کاربر"):
        create_initial_admin(
            db,
            username="second.admin",
            display_name="مدیر دوم",
            password="another secure password",
        )

    assert db.scalar(select(func.count(User.id))) == 1


@pytest.mark.parametrize(
    ("username", "display_name", "password"),
    [
        ("ab", "مدیر", "a secure initial password"),
        ("valid.admin", "", "a secure initial password"),
        ("valid.admin", "مدیر", "short"),
    ],
)
def test_bootstrap_rejects_invalid_identity_input(db, username, display_name, password):
    with pytest.raises(BootstrapError):
        create_initial_admin(
            db,
            username=username,
            display_name=display_name,
            password=password,
        )
    assert db.scalar(select(func.count(User.id))) == 0
