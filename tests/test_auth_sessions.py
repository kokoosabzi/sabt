import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.auth.service import create_session, get_user_by_token, revoke_session
from app.db.base import Base
from app.db.models import Session as AuthSession, User


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


def make_user(db: Session) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        username="session-user",
        password_hash=hash_password("a strong test password"),
        display_name="Session User",
        active=True,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(user)
    db.commit()
    return user


def test_session_token_is_hashed_and_resolves_user(db: Session) -> None:
    user = make_user(db)
    token = create_session(db, user)

    row = db.scalar(select(AuthSession))
    assert row is not None
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert row.token_hash != token
    assert get_user_by_token(db, token).id == user.id


def test_revoked_session_is_rejected(db: Session) -> None:
    user = make_user(db)
    token = create_session(db, user)

    revoke_session(db, token)

    assert get_user_by_token(db, token) is None


def test_expired_session_is_rejected_with_sqlite_naive_datetime(db: Session) -> None:
    user = make_user(db)
    token = create_session(db, user)
    row = db.scalar(select(AuthSession))
    assert row is not None
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert get_user_by_token(db, token) is None


def test_unknown_session_token_is_rejected(db: Session) -> None:
    make_user(db)
    assert get_user_by_token(db, "unknown-token") is None


def test_session_is_rejected_after_user_is_deactivated(db: Session) -> None:
    user = make_user(db)
    token = create_session(db, user)

    user.active = False
    db.commit()

    assert get_user_by_token(db, token) is None
