from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.authorization import AuthorizationContext, authorize, has_permission
from app.auth.passwords import hash_password, verify_password
from app.db.base import Base
from app.db.models import (
    Permission,
    Project,
    ProjectAccess,
    Role,
    RolePermission,
    User,
    UserRole,
)


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


def seed_identity(db: Session, *, active: bool = True):
    now = datetime.now(timezone.utc)
    user = User(
        username="tester",
        password_hash=hash_password("correct horse battery staple"),
        display_name="Test User",
        active=active,
        created_at=now,
        updated_at=now,
        version=1,
    )
    project = Project(
        code="P1",
        name="Project One",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    role = Role(code="operator", name="Operator", active=True)
    permission = Permission(code="operation.edit", name="Edit operation")
    db.add_all([user, project, role, permission])
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.flush()
    return user, project, role, permission, now


def test_password_hash_verifies_only_correct_password():
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
    assert not verify_password("password", "not-a-valid-hash")


def test_global_role_requires_project_access_for_project_permission(db: Session):
    user, project, role, permission, now = seed_identity(db)
    db.add(UserRole(user_id=user.id, role_id=role.id, project_id=None))
    db.flush()

    assert not has_permission(db, user, permission.code, project.id)

    db.add(
        ProjectAccess(
            user_id=user.id,
            project_id=project.id,
            active=True,
            granted_at=now,
            version=1,
        )
    )
    db.flush()
    assert has_permission(db, user, permission.code, project.id)
    authorize(db, user, permission.code, AuthorizationContext(project_id=project.id))


def test_project_role_without_project_access_is_denied(db: Session):
    user, project, role, permission, _ = seed_identity(db)
    db.add(UserRole(user_id=user.id, role_id=role.id, project_id=project.id))
    db.flush()

    assert not has_permission(db, user, permission.code, project.id)
    with pytest.raises(PermissionError, match="forbidden"):
        authorize(db, user, permission.code, AuthorizationContext(project_id=project.id))


def test_project_access_without_permission_is_denied(db: Session):
    user, project, _, permission, now = seed_identity(db)
    db.add(
        ProjectAccess(
            user_id=user.id,
            project_id=project.id,
            active=True,
            granted_at=now,
            version=1,
        )
    )
    db.flush()

    assert not has_permission(db, user, permission.code, project.id)


def test_inactive_user_is_denied_even_with_permission_and_access(db: Session):
    user, project, role, permission, now = seed_identity(db, active=False)
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, project_id=None),
            ProjectAccess(
                user_id=user.id,
                project_id=project.id,
                active=True,
                granted_at=now,
                version=1,
            ),
        ]
    )
    db.flush()

    with pytest.raises(PermissionError, match="inactive_user"):
        authorize(db, user, permission.code, AuthorizationContext(project_id=project.id))


def test_global_permission_check_does_not_accept_project_only_role(db: Session):
    user, project, role, permission, now = seed_identity(db)
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, project_id=project.id),
            ProjectAccess(
                user_id=user.id,
                project_id=project.id,
                active=True,
                granted_at=now,
                version=1,
            ),
        ]
    )
    db.flush()

    assert not has_permission(db, user, permission.code)

def test_inactive_role_is_denied_even_when_user_has_project_access(db: Session):
    user, project, role, permission, now = seed_identity(db)
    role.active = False
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, project_id=None),
            ProjectAccess(
                user_id=user.id,
                project_id=project.id,
                active=True,
                granted_at=now,
                version=1,
            ),
        ]
    )
    db.flush()

    assert not has_permission(db, user, permission.code, project.id)
    with pytest.raises(PermissionError, match="forbidden"):
        authorize(db, user, permission.code, AuthorizationContext(project_id=project.id))


def test_revoked_project_access_denies_permission(db: Session):
    user, project, role, permission, now = seed_identity(db)
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id, project_id=None),
            ProjectAccess(
                user_id=user.id,
                project_id=project.id,
                active=False,
                granted_at=now,
                revoked_at=now,
                version=2,
            ),
        ]
    )
    db.flush()

    assert not has_permission(db, user, permission.code, project.id)
    with pytest.raises(PermissionError, match="forbidden"):
        authorize(db, user, permission.code, AuthorizationContext(project_id=project.id))

