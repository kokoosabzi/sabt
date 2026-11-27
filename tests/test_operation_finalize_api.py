from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    Operation, OperationParty, OperationType, OperationTypeWorkflow, PartyRole, Permission, Person,
    PersonSnapshot, Project, ProjectAccess, ProjectOperationType, ProjectPerson, ProjectProperty,
    Property, PropertySnapshot, Role, RolePermission, User, UserRole, WorkflowEvent, OperationVersion,
)
from app.main import app


@pytest.fixture()
def api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="finalize-api-user", password_hash="unused", display_name="Finalize API",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="FINALIZE-API", contract_code="76", name="Finalize API Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    operation_type = OperationType(code="FINALIZE-TEST", name="Transfer", active=True, system_defined=False,
                                   created_at=now, updated_at=now)
    person = Person(first_name="Buyer", last_name="Transferee", created_at=now, updated_at=now, version=1, is_active=True)
    property_record = Property(unit_number="101", address="Test unit", created_at=now, updated_at=now, version=1, is_active=True)
    party_role = PartyRole(code="BUYER_TRANSFEREE", name="Buyer / Transferee", active=True,
                           system_defined=True, created_at=now, updated_at=now)
    role = Role(code="finalize-api-role", name="Finalize API Role", active=True)
    edit_permission = Permission(code="operation.edit", name="Edit operation")
    finalize_permission = Permission(code="operation.finalize", name="Finalize operation")
    db.add_all([user, project, operation_type, person, property_record, party_role, role, edit_permission, finalize_permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=edit_permission.id),
        RolePermission(role_id=role.id, permission_id=finalize_permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=person.id, active=True, created_at=now, updated_at=now),
        ProjectProperty(project_id=project.id, property_id=property_record.id, active=True, created_at=now, updated_at=now),
        ProjectOperationType(project_id=project.id, operation_type_id=operation_type.id, enabled=True,
                             created_at=now, updated_at=now, version=1),
    ])
    db.flush()
    db.add_all([
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="DRAFT", sequence_no=1, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="IN_PROGRESS", sequence_no=2, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="READY_FOR_FINALIZATION", sequence_no=3, active=True),
    ])
    operation = Operation(project_id=project.id, operation_type_id=operation_type.id, property_id=property_record.id,
                          status="DRAFT", current_workflow_state="DRAFT", created_by=user.id, created_at=now,
                          updated_at=now, version=1, current_version_number=0)
    db.add(operation)
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        yield TestClient(app), db, user, project, operation, person, party_role, role, finalize_permission
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def advance_to_ready(client, operation, person, party_role):
    party = client.post(f"/operations/{operation.id}/parties", json={
        "person_id": person.id, "role_id": party_role.id, "sequence_no": 1, "expected_version": 1,
    })
    assert party.status_code == 201
    in_progress = client.post(f"/operations/{operation.id}/transition", json={
        "target_state": "IN_PROGRESS", "expected_version": 2,
    })
    assert in_progress.status_code == 200
    ready = client.post(f"/operations/{operation.id}/transition", json={
        "target_state": "READY_FOR_FINALIZATION", "expected_version": 3,
    })
    assert ready.status_code == 200
    return ready


def test_finalize_operation_route_is_registered():
    assert "post" in app.openapi()["paths"]["/operations/{operation_id}/finalize"]


def test_finalize_operation_api_commits_version_snapshots_and_event(api_context):
    client, db, _, _, operation, person, party_role, _, _ = api_context
    advance_to_ready(client, operation, person, party_role)
    response = client.post(f"/operations/{operation.id}/finalize", json={
        "expected_version": 4, "reason": "All documents verified",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FINALIZED"
    assert body["workflow_state"] == "FINALIZED"
    assert body["version_number"] == 1
    assert body["operation_version_id"] > 0
    db.refresh(operation)
    assert operation.status == "FINALIZED"
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation.id)) == 1
    assert db.scalar(select(func.count()).select_from(PersonSnapshot).where(PersonSnapshot.operation_id == operation.id)) == 1
    assert db.scalar(select(func.count()).select_from(PropertySnapshot).where(PropertySnapshot.operation_id == operation.id)) == 1
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id, WorkflowEvent.event_type == "OPERATION_FINALIZED")) == 1


def test_finalize_operation_api_rejects_stale_version_without_side_effects(api_context):
    client, db, _, _, operation, person, party_role, _, _ = api_context
    advance_to_ready(client, operation, person, party_role)
    response = client.post(f"/operations/{operation.id}/finalize", json={"expected_version": 3})
    assert response.status_code == 409
    assert response.json()["detail"] == "stale_operation"
    db.refresh(operation)
    assert operation.current_workflow_state == "READY_FOR_FINALIZATION"
    assert operation.version == 4
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation.id)) == 0


def test_finalize_operation_api_rejects_missing_permission_without_side_effects(api_context):
    client, db, _, _, operation, person, party_role, role, permission = api_context
    advance_to_ready(client, operation, person, party_role)
    db.delete(db.get(RolePermission, (role.id, permission.id)))
    db.commit()
    response = client.post(f"/operations/{operation.id}/finalize", json={"expected_version": 4})
    assert response.status_code == 403
    db.refresh(operation)
    assert operation.current_workflow_state == "READY_FOR_FINALIZATION"
    assert operation.version == 4
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation.id)) == 0


def test_finalize_operation_api_rejects_operation_not_ready(api_context):
    client, db, _, _, operation, _, _, _, _ = api_context
    response = client.post(f"/operations/{operation.id}/finalize", json={"expected_version": 1})
    assert response.status_code == 422
    assert response.json()["detail"] == "operation_not_ready_for_finalization"
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation.id)) == 0


def test_finalize_operation_api_requires_authentication(api_context):
    client, db, _, _, operation, person, party_role, _, _ = api_context
    advance_to_ready(client, operation, person, party_role)
    app.dependency_overrides.pop(current_user)
    response = client.post(f"/operations/{operation.id}/finalize", json={"expected_version": 4})
    assert response.status_code == 401
    db.refresh(operation)
    assert operation.current_workflow_state == "READY_FOR_FINALIZATION"
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation.id)) == 0