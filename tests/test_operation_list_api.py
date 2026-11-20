from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    Operation, OperationType, ParentContract, Permission, Person, Project,
    ProjectAccess, ProjectOperationType, ProjectPerson, Role, RolePermission,
    User, UserRole,
)
from app.main import app


@pytest.fixture()
def api_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(
        username="operation-list-user", password_hash="unused",
        display_name="Operation List", active=True,
        created_at=now, updated_at=now, version=1,
    )
    project = Project(
        code="OP-LIST", contract_code="76", name="Operation List Project",
        status="ACTIVE", timezone="Asia/Tehran",
        created_at=now, updated_at=now, version=1,
    )
    operation_type = OperationType(
        code="TRANSFER", name="انتقال مالکیت", active=True,
        system_defined=True, created_at=now, updated_at=now,
    )
    person = Person(
        first_name="Initial", last_name="Owner",
        created_at=now, updated_at=now, version=1, is_active=True,
    )
    role = Role(code="operation-list-role", name="Operation List", active=True)
    permission = Permission(code="operation.view", name="View Operations")
    db.add_all([user, project, operation_type, person, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True,
                      granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=person.id, active=True,
                      created_at=now, updated_at=now),
        ProjectOperationType(project_id=project.id, operation_type_id=operation_type.id,
                             enabled=True, created_at=now, updated_at=now, version=1),
    ])
    db.flush()
    parent = ParentContract(
        project_id=project.id, contract_number="760123", suffix="0123",
        initial_person_id=person.id, property_id=None, status="ACTIVE",
        created_at=now, updated_at=now, version=1, next_transfer_sequence=1,
    )
    db.add(parent)
    db.flush()
    first = Operation(
        project_id=project.id, operation_type_id=operation_type.id,
        parent_contract_id=parent.id, status="DRAFT", current_workflow_state="DRAFT",
        created_by=user.id, created_at=now, updated_at=now, version=1,
        current_version_number=0,
    )
    second = Operation(
        project_id=project.id, operation_type_id=operation_type.id,
        status="FINALIZED", current_workflow_state="FINALIZED",
        created_by=user.id, created_at=now + timedelta(seconds=1),
        updated_at=now + timedelta(seconds=1), finalized_at=now + timedelta(seconds=1),
        version=2, current_version_number=1,
    )
    db.add_all([first, second])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        yield TestClient(app), db, project, first, second, role, permission
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_operations_list_is_project_scoped_paginated_and_includes_parent_contract(api_context):
    client, _, project, first, second, _, _ = api_context

    response = client.get(f"/operations?project_id={project.id}&limit=1&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project.id
    assert body["pagination"] == {
        "limit": 1, "offset": 0, "total": 2, "has_more": True,
    }
    assert body["items"][0]["operation_id"] == second.id
    assert body["items"][0]["status"] == "FINALIZED"
    next_page = client.get(f"/operations?project_id={project.id}&limit=1&offset=1")
    assert next_page.status_code == 200
    assert next_page.json()["items"][0]["operation_id"] == first.id
    assert next_page.json()["items"][0]["parent_contract_number"] == "760123"


def test_operations_list_can_filter_by_status(api_context):
    client, _, project, first, _, _, _ = api_context

    response = client.get(f"/operations?project_id={project.id}&status=DRAFT")

    assert response.status_code == 200
    assert [item["operation_id"] for item in response.json()["items"]] == [first.id]


def test_operations_list_requires_authentication_and_project_view_permission(api_context):
    client, db, project, _, _, role, permission = api_context

    assert client.get(f"/operations?project_id={project.id}").status_code == 401

    app.dependency_overrides[current_user] = lambda: db.query(User).filter_by(
        username="operation-list-user"
    ).one()
    db.query(RolePermission).filter_by(
        role_id=role.id, permission_id=permission.id
    ).delete()
    db.commit()
    denied = client.get(
        f"/operations?project_id={project.id}",
        headers={"Authorization": "Bearer unused"},
    )
    # The dependency override represents an authenticated user; authorization
    # must still deny the list after its project-scoped permission is removed.
    assert denied.status_code == 403
