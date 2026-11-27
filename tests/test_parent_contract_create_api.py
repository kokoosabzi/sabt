from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    ParentContract, Permission, Person, Project, ProjectAccess, ProjectPerson,
    Property, ProjectProperty, Role, RolePermission, User, UserRole,
)
from app.main import app


@pytest.fixture()
def api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="contract-create-api", password_hash="unused", display_name="Contract API",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="CONTRACT-API", contract_code="76", name="Contract API Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    person = Person(first_name="Initial", last_name="Owner", created_at=now, updated_at=now,
                    version=1, is_active=True)
    role = Role(code="contract-create-role", name="Contract Create", active=True)
    permission = Permission(code="parent_contract.create", name="Create Parent Contract")
    db.add_all([user, project, person, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=person.id, active=True, created_at=now, updated_at=now),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        yield TestClient(app), db, user, project, person, role, permission
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_manual_parent_contract_creation_uses_project_code_and_preserves_leading_zeroes(api_context):
    client, db, _, project, person, _, _ = api_context
    response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": person.id,
    })
    assert response.status_code == 201
    body = response.json()
    assert body["contract_number"] == "760123"
    assert body["suffix"] == "0123"
    assert body["initial_person_id"] == person.id
    assert db.scalar(select(func.count()).select_from(ParentContract)) == 1


def test_manual_parent_contract_creation_rejects_duplicate_suffix_without_writes(api_context):
    client, db, _, project, person, _, _ = api_context
    first = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": person.id,
    })
    assert first.status_code == 201
    second = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": person.id,
    })
    assert second.status_code == 409
    assert second.json()["detail"] == "parent_contract_suffix_exists"
    assert db.scalar(select(func.count()).select_from(ParentContract)) == 1


def test_manual_parent_contract_creation_rejects_invalid_suffix(api_context):
    client, db, _, project, person, _, _ = api_context
    response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "12A4", "initial_person_id": person.id,
    })
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(ParentContract)) == 0


def test_manual_parent_contract_creation_requires_project_permission(api_context):
    client, db, _, project, person, role, permission = api_context
    db.delete(db.get(RolePermission, (role.id, permission.id)))
    db.commit()
    response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": person.id,
    })
    assert response.status_code == 403
    assert db.scalar(select(func.count()).select_from(ParentContract)) == 0


def test_manual_parent_contract_creation_requires_authentication(api_context):
    client, db, _, project, person, _, _ = api_context
    app.dependency_overrides.pop(current_user)
    response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": person.id,
    })
    assert response.status_code == 401
    assert db.scalar(select(func.count()).select_from(ParentContract)) == 0

def test_parent_contract_options_returns_only_active_project_associations(api_context):
    client, db, _, project, person, _, _ = api_context
    now = datetime.now(timezone.utc)
    active_property = Property(
        block_tower="Tower A", floor="2", unit_number="12",
        created_at=now, updated_at=now, version=1, is_active=True,
    )
    inactive_property = Property(
        block_tower="Tower B", floor="1", unit_number="3",
        created_at=now, updated_at=now, version=1, is_active=False,
    )
    inactive_person = Person(
        first_name="Inactive", last_name="Person",
        created_at=now, updated_at=now, version=1, is_active=True,
    )
    db.add_all([active_property, inactive_property, inactive_person])
    db.flush()
    db.add_all([
        ProjectProperty(
            project_id=project.id, property_id=active_property.id, active=True,
            created_at=now, updated_at=now,
        ),
        ProjectProperty(
            project_id=project.id, property_id=inactive_property.id, active=True,
            created_at=now, updated_at=now,
        ),
        ProjectPerson(
            project_id=project.id, person_id=inactive_person.id, active=False,
            created_at=now, updated_at=now,
        ),
    ])
    db.commit()

    response = client.get(f"/contracts/parent/options?project_id={project.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == {
        "id": project.id, "name": project.name, "contract_code": "76",
    }
    assert [item["id"] for item in payload["people"]] == [person.id]
    assert [item["id"] for item in payload["properties"]] == [active_property.id]


def test_parent_contract_options_requires_project_create_permission(api_context):
    client, db, _, project, _, role, permission = api_context
    db.delete(db.get(RolePermission, (role.id, permission.id)))
    db.commit()

    response = client.get(f"/contracts/parent/options?project_id={project.id}")

    assert response.status_code == 403


def test_parent_contract_options_rejects_missing_project(api_context):
    client, _, _, _, _, _, _ = api_context

    response = client.get("/contracts/parent/options?project_id=999999")

    assert response.status_code == 404
