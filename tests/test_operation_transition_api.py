from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    Operation, OperationParty, OperationType, OperationTypeWorkflow, PartyRole, Permission, Person, Project,
    ProjectAccess, ProjectOperationType, ProjectPerson, Role, RolePermission, User, UserRole,
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
    person = Person(first_name="Test", last_name="Party", created_at=now,
                    updated_at=now, version=1, is_active=True)
    party_role = PartyRole(code="TEST_PARTY", name="Test Party", active=True,
                           system_defined=False, created_at=now, updated_at=now)
    permission = Permission(code="operation.edit", name="Edit operation")
    view_permission = Permission(code="operation.view", name="View operation")
    create_permission = Permission(code="operation.create", name="Create operation")
    db.add_all([user, project, operation_type, role, person, party_role,
                permission, view_permission, create_permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        RolePermission(role_id=role.id, permission_id=view_permission.id),
        RolePermission(role_id=role.id, permission_id=create_permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True,
                      granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=person.id, active=True,
                      created_at=now, updated_at=now),
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
    # FastAPI's newer router implementation may defer included routes; OpenAPI
    # is the stable public contract for asserting the registered endpoint.
    assert "post" in app.openapi()["paths"]["/operations/{operation_id}/transition"]


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

def test_operation_transition_rejects_user_without_project_access(api_context) -> None:
    client, db, user, project, operation = api_context
    db.query(ProjectAccess).filter_by(user_id=user.id, project_id=project.id).delete()
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
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "OPERATION_WORKFLOW_TRANSITIONED",
    )) == 0

def test_operation_transition_rejects_permission_scoped_to_another_project(api_context) -> None:
    client, db, user, project, operation = api_context
    now = datetime.now(timezone.utc)
    other_project = Project(
        code="TRANSITION-OTHER",
        name="Other Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(other_project)
    db.flush()
    db.query(UserRole).filter_by(user_id=user.id).update(
        {UserRole.project_id: other_project.id}
    )
    db.commit()

    # The user still has access to the operation's project, but the edit role
    # is scoped to a different project and must not authorize this transition.
    assert db.query(ProjectAccess).filter_by(
        user_id=user.id, project_id=project.id, active=True
    ).count() == 1
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"
    db.refresh(operation)
    assert operation.current_workflow_state == "DRAFT"
    assert operation.version == 1



def test_operation_transition_cannot_access_operation_in_another_project(api_context) -> None:
    client, db, user, project, _ = api_context
    now = datetime.now(timezone.utc)
    other_project = Project(
        code="TRANSITION-FOREIGN",
        name="Foreign Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(other_project)
    db.flush()
    operation_type = db.query(OperationType).filter_by(code="TRANSITION-TEST").one()
    db.add(ProjectOperationType(
        project_id=other_project.id,
        operation_type_id=operation_type.id,
        enabled=True,
        created_at=now,
        updated_at=now,
        version=1,
    ))
    db.flush()
    foreign_operation = Operation(
        project_id=other_project.id,
        operation_type_id=operation_type.id,
        status="DRAFT",
        current_workflow_state="DRAFT",
        created_by=user.id,
        created_at=now,
        updated_at=now,
        version=1,
        current_version_number=0,
    )
    db.add(foreign_operation)
    db.add_all([
        OperationTypeWorkflow(
            project_id=other_project.id,
            operation_type_id=foreign_operation.operation_type_id,
            state_code="DRAFT",
            sequence_no=1,
            active=True,
        ),
        OperationTypeWorkflow(
            project_id=other_project.id,
            operation_type_id=foreign_operation.operation_type_id,
            state_code="IN_PROGRESS",
            sequence_no=2,
            active=True,
        ),
    ])
    db.commit()

    # Access to the fixture project must not grant access to an operation
    # whose owning project is different.
    assert db.query(ProjectAccess).filter_by(
        user_id=user.id, project_id=project.id, active=True
    ).count() == 1
    assert db.query(ProjectAccess).filter_by(
        user_id=user.id, project_id=other_project.id, active=True
    ).count() == 0
    response = client.post(
        f"/operations/{foreign_operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"
    db.refresh(foreign_operation)
    assert foreign_operation.current_workflow_state == "DRAFT"
    assert foreign_operation.version == 1
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == foreign_operation.id,
        WorkflowEvent.event_type == "OPERATION_WORKFLOW_TRANSITIONED",
    )) == 0



def test_get_operation_returns_details_with_project_view_permission(api_context) -> None:
    client, _, _, project, operation = api_context
    response = client.get(f"/operations/{operation.id}")

    assert response.status_code == 200
    assert response.json()["operation_id"] == operation.id
    assert response.json()["project_id"] == project.id
    assert response.json()["workflow_state"] == "DRAFT"
    assert response.json()["version"] == 1


def test_get_operation_rejects_user_without_view_permission(api_context) -> None:
    client, db, _, _, operation = api_context
    db.query(RolePermission).filter(
        RolePermission.permission_id == db.query(Permission.id).filter_by(code="operation.view").scalar_subquery()
    ).delete(synchronize_session=False)
    db.commit()

    response = client.get(f"/operations/{operation.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"


def test_get_operation_returns_not_found_for_missing_operation(api_context) -> None:
    client, _, _, _, _ = api_context
    response = client.get("/operations/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "operation_not_found"



def test_create_operation_creates_draft_and_event(api_context) -> None:
    client, db, _, project, operation = api_context
    response = client.post(
        "/operations",
        json={"project_id": project.id, "operation_type_id": operation.operation_type_id},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project_id"] == project.id
    assert payload["operation_type_id"] == operation.operation_type_id
    assert payload["status"] == "DRAFT"
    assert payload["workflow_state"] == "DRAFT"
    assert payload["version"] == 1
    created_id = payload["operation_id"]
    created = db.get(Operation, created_id)
    assert created is not None
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == created_id,
        WorkflowEvent.event_type == "OPERATION_CREATED",
    )) == 1


def test_create_operation_requires_project_access(api_context) -> None:
    client, db, user, project, operation = api_context
    db.query(ProjectAccess).filter_by(user_id=user.id, project_id=project.id).delete()
    db.commit()

    response = client.post(
        "/operations",
        json={"project_id": project.id, "operation_type_id": operation.operation_type_id},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"
    assert db.scalar(select(func.count()).select_from(Operation)) == 1


def test_create_operation_rejects_inactive_or_unenabled_type(api_context) -> None:
    client, db, _, project, operation = api_context
    db.query(ProjectOperationType).filter_by(
        project_id=project.id, operation_type_id=operation.operation_type_id
    ).update({"enabled": False})
    db.commit()

    response = client.post(
        "/operations",
        json={"project_id": project.id, "operation_type_id": operation.operation_type_id},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "operation_type_not_enabled_for_project"
    assert db.scalar(select(func.count()).select_from(Operation)) == 1



def test_add_operation_party_succeeds_and_increments_operation_version(api_context) -> None:
    client, db, _, project, operation = api_context
    person = db.query(Person).filter_by(first_name="Test", last_name="Party").one()
    role = db.query(PartyRole).filter_by(code="TEST_PARTY").one()

    response = client.post(
        f"/operations/{operation.id}/parties",
        json={"person_id": person.id, "role_id": role.id, "sequence_no": 1, "expected_version": 1},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["operation_id"] == operation.id
    assert payload["project_id"] == project.id
    assert payload["person_id"] == person.id
    assert payload["role_id"] == role.id
    db.refresh(operation)
    assert operation.version == 2
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "PARTY_ADDED",
    )) == 1


def test_add_operation_party_rejects_stale_version(api_context) -> None:
    client, db, _, _, operation = api_context
    person = db.query(Person).filter_by(first_name="Test", last_name="Party").one()
    role = db.query(PartyRole).filter_by(code="TEST_PARTY").one()

    response = client.post(
        f"/operations/{operation.id}/parties",
        json={"person_id": person.id, "role_id": role.id, "sequence_no": 1, "expected_version": 9},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "stale_operation"
    assert db.scalar(select(func.count()).select_from(OperationParty).where(
        OperationParty.operation_id == operation.id,
    )) == 0



def test_list_operation_parties_returns_project_scoped_party_details(api_context) -> None:
    client, db, _, _, operation = api_context
    person = db.query(Person).filter_by(first_name="Test", last_name="Party").one()
    role = db.query(PartyRole).filter_by(code="TEST_PARTY").one()
    response = client.post(
        f"/operations/{operation.id}/parties",
        json={"person_id": person.id, "role_id": role.id, "sequence_no": 1, "expected_version": 1},
    )
    assert response.status_code == 201

    response = client.get(f"/operations/{operation.id}/parties")

    assert response.status_code == 200
    assert response.json()["operation_id"] == operation.id
    assert len(response.json()["parties"]) == 1
    assert response.json()["parties"][0]["person_id"] == person.id
    assert response.json()["parties"][0]["role_code"] == role.code


def test_list_operation_parties_requires_view_permission(api_context) -> None:
    client, db, _, _, operation = api_context
    db.query(RolePermission).filter(
        RolePermission.permission_id == db.query(Permission.id).filter_by(code="operation.view").scalar_subquery()
    ).delete(synchronize_session=False)
    db.commit()

    response = client.get(f"/operations/{operation.id}/parties")

    assert response.status_code == 403
    assert response.json()["detail"] == "forbidden"



def test_operation_read_endpoints_reject_another_project(api_context) -> None:
    client, db, user, project, operation = api_context
    now = datetime.now(timezone.utc)
    other_project = Project(
        code="TRANSITION-READ-OTHER",
        name="Other Read Project",
        status="ACTIVE",
        timezone="Asia/Tehran",
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(other_project)
    db.flush()
    db.add(ProjectOperationType(
        project_id=other_project.id,
        operation_type_id=operation.operation_type_id,
        enabled=True,
        created_at=now,
        updated_at=now,
        version=1,
    ))
    db.flush()
    foreign_operation = Operation(
        project_id=other_project.id,
        operation_type_id=operation.operation_type_id,
        status="DRAFT",
        current_workflow_state="DRAFT",
        created_by=user.id,
        created_at=now,
        updated_at=now,
        version=1,
        current_version_number=0,
    )
    db.add(foreign_operation)
    db.commit()

    # Global view permission and access to the fixture project must not grant
    # access to operation details or party details from a different project.
    for path in (
        f"/operations/{foreign_operation.id}",
        f"/operations/{foreign_operation.id}/parties",
    ):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

def test_operation_transition_rejects_version_changed_after_initial_read(api_context, monkeypatch) -> None:
    # Simulate another request winning after this request's initial version
    # check but before its conditional UPDATE.
    from sqlalchemy import update
    from app.operations import service as operation_service

    client, db, _, _, operation = api_context

    def concurrent_change():
        db.execute(
            update(Operation)
            .where(Operation.id == operation.id)
            .values(
                current_workflow_state="IN_PROGRESS",
                status="IN_PROGRESS",
                version=Operation.version + 1,
            )
        )
        return datetime.now(timezone.utc)

    monkeypatch.setattr(operation_service, "_now", concurrent_change)
    response = client.post(
        f"/operations/{operation.id}/transition",
        json={"target_state": "IN_PROGRESS", "expected_version": 1},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "stale_operation"
    db.rollback()
    db.refresh(operation)
    assert operation.current_workflow_state == "DRAFT"
    assert operation.version == 1
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "OPERATION_WORKFLOW_TRANSITIONED",
    )) == 0

def test_add_operation_party_rejects_version_changed_after_initial_read(api_context, monkeypatch) -> None:
    from sqlalchemy import update
    from app.operations import service as operation_service

    client, db, _, _, operation = api_context
    person = db.query(Person).filter_by(first_name="Test", last_name="Party").one()
    role = db.query(PartyRole).filter_by(code="TEST_PARTY").one()

    def concurrent_change():
        db.execute(
            update(Operation)
            .where(Operation.id == operation.id)
            .values(version=Operation.version + 1)
        )
        return datetime.now(timezone.utc)

    monkeypatch.setattr(operation_service, "_now", concurrent_change)
    response = client.post(
        f"/operations/{operation.id}/parties",
        json={
            "person_id": person.id,
            "role_id": role.id,
            "sequence_no": 1,
            "expected_version": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "stale_operation"
    db.rollback()
    db.refresh(operation)
    assert operation.version == 1
    assert db.scalar(select(func.count()).select_from(OperationParty).where(
        OperationParty.operation_id == operation.id,
    )) == 0
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation.id,
        WorkflowEvent.event_type == "PARTY_ADDED",
    )) == 0

