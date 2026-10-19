from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_db
from app.auth.passwords import hash_password
from app.db.base import Base
from app.db.models import Session as AuthSession, User
from app.main import app


@pytest.fixture()
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _create_user(engine, username: str, *, active: bool = True) -> None:
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(User(
            username=username,
            password_hash=hash_password("correct test password"),
            display_name=username,
            active=active,
            created_at=now,
            updated_at=now,
            version=1,
        ))
        db.commit()


def test_login_me_and_logout_revoke_the_bearer_session(api_client):
    client, engine = api_client
    _create_user(engine, "api-session-user")

    login = client.post(
        "/auth/login",
        auth=("api-session-user", "correct test password"),
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 28800

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "api-session-user"

    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    assert logout.json() == {"status": "ok"}
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    with Session(engine) as db:
        session = db.scalar(select(AuthSession))
        assert session is not None
        assert session.revoked_at is not None


def test_login_rejects_wrong_password_and_inactive_account(api_client):
    client, engine = api_client
    _create_user(engine, "active-api-user")
    _create_user(engine, "inactive-api-user", active=False)

    wrong_password = client.post(
        "/auth/login",
        auth=("active-api-user", "wrong password"),
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"] == "Invalid credentials"

    inactive_user = client.post(
        "/auth/login",
        auth=("inactive-api-user", "correct test password"),
    )
    assert inactive_user.status_code == 401
    assert inactive_user.json()["detail"] == "Invalid credentials"


def test_auth_me_rejects_expired_session_at_the_api_boundary(api_client):
    client, engine = api_client
    _create_user(engine, "expired-api-user")
    login = client.post(
        "/auth/login",
        auth=("expired-api-user", "correct test password"),
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    with Session(engine) as db:
        session = db.scalar(select(AuthSession))
        assert session is not None
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired session"
