from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    Operation, OperationType, OperationTypeWorkflow, OperationVersion, PartyRole, Permission, Person,
    PersonSnapshot, Project, ProjectAccess, ProjectOperationType, ProjectPerson, ProjectProperty,
    Property, PropertySnapshot, Role, RolePermission, User, UserRole, WorkflowEvent, ParentContract,
)
from app.main import app


@pytest.fixture()
def transfer_api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="transfer-api-user", password_hash="unused", display_name="Transfer API",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="TRANSFER-API", contract_code="76", name="Transfer API Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    operation_type = OperationType(code="TRANSFER-API", name="Transfer", active=True, system_defined=False,
                                   created_at=now, updated_at=now)
    initial_owner = Person(first_name="Initial", last_name="Owner", created_at=now, updated_at=now, version=1, is_active=True)
    buyer = Person(first_name="Approved", last_name="Transferee", created_at=now, updated_at=now, version=1, is_active=True)
    property_record = Property(unit_number="101", address="Transfer test unit", created_at=now, updated_at=now, version=1, is_active=True)
    buyer_role = PartyRole(code="BUYER_TRANSFEREE", name="Buyer / Transferee", active=True,
                           system_defined=True, created_at=now, updated_at=now)
    role = Role(code="transfer-api-role", name="Transfer API Role", active=True)
    permission_codes = ["operation.create", "operation.edit", "operation.finalize", "parent_contract.create", "parent_contract.view"]
    permissions = [Permission(code=code, name=code) for code in permission_codes]
    db.add_all([user, project, operation_type, initial_owner, buyer, property_record, buyer_role, role, *permissions])
    db.flush()
    db.add_all([RolePermission(role_id=role.id, permission_id=permission.id) for permission in permissions])
    db.add_all([
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=initial_owner.id, active=True, created_at=now, updated_at=now),
        ProjectPerson(project_id=project.id, person_id=buyer.id, active=True, created_at=now, updated_at=now),
        ProjectProperty(project_id=project.id, property_id=property_record.id, active=True, created_at=now, updated_at=now),
        ProjectOperationType(project_id=project.id, operation_type_id=operation_type.id, enabled=True, created_at=now, updated_at=now, version=1),
    ])
    db.add_all([
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="DRAFT", sequence_no=1, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="IN_PROGRESS", sequence_no=2, active=True),
        OperationTypeWorkflow(project_id=project.id, operation_type_id=operation_type.id, state_code="READY_FOR_FINALIZATION", sequence_no=3, active=True),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        yield TestClient(app), db, project, operation_type, initial_owner, buyer, property_record, buyer_role
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_parent_contract_transfer_api_allocates_child_and_changes_current_owner(transfer_api_context):
    client, db, project, operation_type, initial_owner, buyer, property_record, buyer_role = transfer_api_context
    parent_response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0123", "initial_person_id": initial_owner.id, "property_id": property_record.id,
    })
    assert parent_response.status_code == 201
    assert parent_response.json()["contract_number"] == "760123"
    parent_id = parent_response.json()["id"]

    operation_response = client.post("/operations", json={
        "project_id": project.id, "operation_type_id": operation_type.id,
        "property_id": property_record.id, "parent_contract_id": parent_id,
    })
    assert operation_response.status_code == 201
    operation_id = operation_response.json()["operation_id"]

    party_response = client.post(f"/operations/{operation_id}/parties", json={
        "person_id": buyer.id, "role_id": buyer_role.id, "sequence_no": 1, "expected_version": 1,
    })
    assert party_response.status_code == 201
    in_progress = client.post(f"/operations/{operation_id}/transition", json={
        "target_state": "IN_PROGRESS", "expected_version": 2,
    })
    assert in_progress.status_code == 200
    ready = client.post(f"/operations/{operation_id}/transition", json={
        "target_state": "READY_FOR_FINALIZATION", "expected_version": 3,
    })
    assert ready.status_code == 200

    finalized = client.post(f"/operations/{operation_id}/finalize", json={
        "expected_version": 4, "reason": "Approved buyer / transferee",
    })
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "FINALIZED"
    assert finalized.json()["child_contract_number"] == "760123/1"
    assert finalized.json()["transfer_sequence"] == 1

    history = client.get("/contracts/parent/760123/history")
    assert history.status_code == 200
    body = history.json()
    assert body["current_owner"]["source"] == "latest_valid_finalized_transfer"
    assert body["current_owner"]["people"][0]["person_id"] == buyer.id
    assert body["current_owner"]["people"][0]["last_name"] == "Transferee"
    assert body["transfers"][0]["child_contract_number"] == "760123/1"

    parent = db.get(ParentContract, parent_id)
    operation = db.get(Operation, operation_id)
    assert parent.next_transfer_sequence == 2
    assert operation.current_version_number == 1
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation_id)) == 1
    assert db.scalar(select(func.count()).select_from(PersonSnapshot).where(PersonSnapshot.operation_id == operation_id)) == 1
    assert db.scalar(select(func.count()).select_from(PropertySnapshot).where(PropertySnapshot.operation_id == operation_id)) == 1
    assert db.scalar(select(func.count()).select_from(WorkflowEvent).where(
        WorkflowEvent.operation_id == operation_id, WorkflowEvent.event_type == "OPERATION_FINALIZED")) == 1


def test_transfer_finalize_without_approved_transferee_rolls_back_sequence(transfer_api_context):
    client, db, project, operation_type, initial_owner, _, property_record, _ = transfer_api_context
    parent_response = client.post("/contracts/parent", json={
        "project_id": project.id, "suffix": "0124", "initial_person_id": initial_owner.id, "property_id": property_record.id,
    })
    assert parent_response.status_code == 201
    parent_id = parent_response.json()["id"]
    operation_response = client.post("/operations", json={
        "project_id": project.id, "operation_type_id": operation_type.id,
        "property_id": property_record.id, "parent_contract_id": parent_id,
    })
    operation_id = operation_response.json()["operation_id"]
    assert operation_response.status_code == 201
    for state, version in [("IN_PROGRESS", 1), ("READY_FOR_FINALIZATION", 2)]:
        response = client.post(f"/operations/{operation_id}/transition", json={
            "target_state": state, "expected_version": version,
        })
        assert response.status_code == 200
    response = client.post(f"/operations/{operation_id}/finalize", json={"expected_version": 3})
    assert response.status_code == 422
    assert response.json()["detail"] == "buyer_transferee_required"
    parent = db.get(ParentContract, parent_id)
    operation = db.get(Operation, operation_id)
    assert parent.next_transfer_sequence == 1
    assert operation.transfer_sequence is None
    assert operation.child_contract_number is None
    assert operation.status != "FINALIZED"
    assert db.scalar(select(func.count()).select_from(OperationVersion).where(OperationVersion.operation_id == operation_id)) == 0