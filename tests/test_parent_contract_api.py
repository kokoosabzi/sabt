from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    ParentContract, Permission, Person, Project, ProjectAccess, Role, RolePermission,
    User, UserRole,
)
from app.main import app


@pytest.fixture()
def api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="api-tester", password_hash="unused", display_name="API Tester",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="API-P", contract_code="76", name="API Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    person = Person(first_name="Initial", last_name="Owner", created_at=now, updated_at=now,
                    version=1, is_active=True)
    role = Role(code="api-viewer", name="API Viewer", active=True)
    permission = Permission(code="parent_contract.view", name="View Parent Contract")
    report_permission = Permission(code="workflow.report.view", name="View Workflow Reports")
    db.add_all([user, project, person, role, permission, report_permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        RolePermission(role_id=role.id, permission_id=report_permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ParentContract(project_id=project.id, contract_number="760123", suffix="0123",
                       initial_person_id=person.id, property_id=None, status="ACTIVE",
                       created_at=now, updated_at=now, version=1, next_transfer_sequence=1),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    client = TestClient(app)
    try:
        yield client, db, user, project
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_parent_contract_history_api_returns_parent_and_owner(api_context):
    client, _, _, _ = api_context
    response = client.get("/contracts/parent/760123/history")
    assert response.status_code == 200
    body = response.json()
    assert body["parent"]["contract_number"] == "760123"
    assert body["current_owner"]["source"] == "initial_contract"
    assert body["current_owner"]["people"][0]["last_name"] == "Owner"
    assert body["transfers"] == []


def test_parent_contract_history_api_rejects_invalid_number(api_context):
    client, _, _, _ = api_context
    response = client.get("/contracts/parent/76A123/history")
    assert response.status_code == 422
    assert response.json()["detail"] == "parent_contract_number_invalid"


def test_parent_contract_history_api_returns_not_found(api_context):
    client, _, _, _ = api_context
    response = client.get("/contracts/parent/760999/history")
    assert response.status_code == 404
    assert response.json()["detail"] == "parent_contract_not_found"


def test_parent_contract_history_api_enforces_project_permission(api_context):
    client, db, _, _ = api_context
    db.query(RolePermission).delete()
    db.commit()
    response = client.get("/contracts/parent/760123/history")
    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"


def test_parent_contract_history_api_requires_authentication(api_context):
    client, _, _, _ = api_context
    app.dependency_overrides.pop(current_user)
    response = client.get("/contracts/parent/760123/history")
    assert response.status_code == 401
