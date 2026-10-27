from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    Operation, OperationType, OperationTypeWorkflow, Permission, Project,
    ProjectAccess, ProjectOperationType, Role, RolePermission, User, UserRole,
    WorkflowEvent,
)
from app.main import app


@pytest.fixture()
def api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="transition-api-tester", password_hash="unused",
                display_name="Transition API Tester", active=True,
                created_at=now, updated_at=now, version=1)
    project = Project(code="TRANSITION-P", name="Transition Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    operation_type = OperationType(code="TRANSITION-TEST", name="Transition Test",
                                   active=True, system_defined=True,
                                   created_at=now, updated_at=now)
    role = Role(code="transition-editor", name="Transition Editor", active=True)
    permission = Permission(code="operation.edit", name="Edit operation")
    db.add_all([user, project, operation_type, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True,
                      granted_at=now, version=1),
        ProjectOperationType(project_id=project.id, operation_type_id=operation_type.id,
                             enabled=True, created_at=now, updated_at=now, version=1),
    ])
    operation = Operation(project_id=project.id, operation_type_id=operation_type.id,
                          status="DRAFT", current_workflow_state="DRAFT",
                          created_by=user.id, created_at=now, updated_at=now,
                          version=1, current_version_number=0)
    db.add(operation)
    db.add_all([
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id,
                              state_code="DRAFT", sequence_no=1, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id,
                              state_code="IN_PROGRESS", sequence_no=2, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id,
                              state_code="READY_FOR_FINALIZATION", sequence_no=3, active=True),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        yield TestClient(app), db, user, project, operation
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_operation_transition_route_is_registered() -> None:
    route = next(route for route in app.routes
                 if getattr(route, "path", None) == "/operations/{operation_id}/transition")
    assert "POST" in route.methods


def test_operation_transition_requires_authentication(api_context) -> None:
    client, _, _, _, operation = api_context
    app.dependency_overrides.pop(current_user)
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )
    assert response.status_code == 401


def test_operation_transition_succeeds_and_records_event(api_context) -> None:
    client, db, _, _, operation = api_context
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1, "reason": "Documents checked"},
    )
    assert response.status_code == 200
    assert response.json()["workflow_state"] == "IN_PROGRESS"
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["version"] == 2
    db.refresh(operation)
    assert operation.current_workflow_state == "IN_PROGRESS"
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "OPERATION_WORKFLOW_TRANSITIONED",
    )) == 1


def test_operation_transition_rejects_stale_version_without_changes(api_context) -> None:
    client, db, _, _, operation = api_context
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 0},
    )
    assert response.status_code == 422  # Request versions must be positive.
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 2},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "stale_operation"
    db.refresh(operation)
    assert operation.current_workflow_state == "DRAFT"
    assert operation.version == 1
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "OPERATION_WORKFLOW_TRANSITIONED",
    )) == 0


def test_operation_transition_rejects_forbidden_user_without_changes(api_context) -> None:
    client, db, _, _, operation = api_context
    db.query(RolePermission).delete()
    db.commit()
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"
    db.refresh(operation)
    assert operation.current_workflow_state == "DRAFT"
    assert operation.version == 1


def test_operation_transition_rejects_invalid_or_skipped_state(api_context) -> None:
    client, db, _, _, operation = api_context
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "READY_FOR_FINALIZATION", "expected_version": 1},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "workflow_transition_not_allowed"
    db.refresh(operation)
    assert operation.current_workflow_state == "DRAFT"
    assert operation.version == 1


def test_operation_transition_returns_not_found(api_context) -> None:
    client, _, _, _, _ = api_context
    response = client.post(
        "/operations/99999/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "operation_not_found"
