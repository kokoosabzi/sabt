from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.passwords import hash_password
from app.bootstrap import create_initial_admin
from app.db.base import Base
from app.db.models import OperationType, OperationTypeWorkflow, PartyRole, Project, ProjectAccess, ProjectOperationType, User
from app.auth.dependencies import get_db
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


def _create_admin(engine):
    with Session(engine) as db:
        create_initial_admin(
            db,
            username="first.admin",
            display_name="مدیر اولیه",
            password="a secure initial password",
        )
        db.commit()


def _login(client):
    response = client.post(
        "/auth/login",
        auth=("first.admin", "a secure initial password"),
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_first_admin_can_create_project_and_receives_active_project_access(api_client):
    client, engine = api_client
    _create_admin(engine)
    headers = _login(client)

    response = client.post(
        "/projects",
        headers=headers,
        json={
            "code": "FIRST-PROJECT",
            "name": "پروژه نخست",
            "contract_code": "76",
            "description": "اولین پروژه عملیاتی",
            "timezone": "Asia/Tehran",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == "first-project"
    assert payload["contract_code"] == "76"
    assert payload["status"] == "ACTIVE"

    with Session(engine) as db:
        project = db.scalar(select(Project).where(Project.code == "first-project"))
        access = db.get(ProjectAccess, (1, project.id))
        assert access is not None
        assert access.active is True
        assert access.granted_by == 1


def test_project_list_contains_only_projects_with_active_membership(api_client):
    client, engine = api_client
    _create_admin(engine)
    headers = _login(client)

    created = client.post(
        "/projects",
        headers=headers,
        json={"code": "visible-project", "name": "پروژه قابل مشاهده", "contract_code": "71"},
    )
    assert created.status_code == 201

    response = client.get("/projects", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["code"] == "visible-project"


def test_project_creation_requires_authentication_and_project_create_permission(api_client):
    client, engine = api_client

    assert client.post(
        "/projects",
        json={"code": "unauthenticated", "name": "بدون ورود", "contract_code": "72"},
    ).status_code == 401

    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(
            User(
                username="ordinary.user",
                password_hash=hash_password("an ordinary user password"),
                display_name="کاربر عادی",
                active=True,
                created_at=now,
                updated_at=now,
                version=1,
            )
        )
        db.commit()

    login = client.post(
        "/auth/login",
        auth=("ordinary.user", "an ordinary user password"),
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.post(
        "/projects",
        headers=headers,
        json={"code": "forbidden-project", "name": "نباید ساخته شود", "contract_code": "73"},
    )
    assert denied.status_code == 403

    with Session(engine) as db:
        assert db.scalar(select(Project)) is None


def test_project_creation_rejects_invalid_contract_code_and_duplicate_codes(api_client):
    client, engine = api_client
    _create_admin(engine)
    headers = _login(client)

    invalid = client.post(
        "/projects",
        headers=headers,
        json={"code": "bad-contract-code", "name": "کد نامعتبر", "contract_code": "01"},
    )
    assert invalid.status_code == 422

    invalid_timezone = client.post(
        "/projects",
        headers=headers,
        json={"code": "bad-timezone", "name": "منطقه زمانی نامعتبر", "contract_code": "78", "timezone": "Not/A_Real_Zone"},
    )
    assert invalid_timezone.status_code == 422

    first = client.post(
        "/projects",
        headers=headers,
        json={"code": "same-code", "name": "پروژه اول", "contract_code": "76"},
    )
    assert first.status_code == 201

    duplicate_internal = client.post(
        "/projects",
        headers=headers,
        json={"code": "SAME-CODE", "name": "تکرار کد", "contract_code": "77"},
    )
    assert duplicate_internal.status_code == 409

    duplicate_contract = client.post(
        "/projects",
        headers=headers,
        json={"code": "different-code", "name": "تکرار کد قرارداد", "contract_code": "76"},
    )
    assert duplicate_contract.status_code == 409

def test_new_project_receives_default_transfer_type_workflow_and_approved_buyer_role(api_client):
    client, engine = api_client
    _create_admin(engine)
    headers = _login(client)
    created = client.post(
        '/projects',
        headers=headers,
        json={'code': 'transfer-defaults', 'name': 'پروژه انتقال', 'contract_code': '82'},
    )
    assert created.status_code == 201
    project_id = created.json()['id']
    with Session(engine) as db:
        transfer_type = db.scalar(select(OperationType).where(OperationType.code == 'TRANSFER'))
        buyer_role = db.scalar(select(PartyRole).where(PartyRole.code == 'BUYER_TRANSFEREE'))
        project_type = db.scalar(select(ProjectOperationType).where(
            ProjectOperationType.project_id == project_id,
            ProjectOperationType.operation_type_id == transfer_type.id,
        ))
        states = set(db.scalars(select(OperationTypeWorkflow.state_code).where(
            OperationTypeWorkflow.project_id == project_id,
            OperationTypeWorkflow.operation_type_id == transfer_type.id,
            OperationTypeWorkflow.active.is_(True),
        )).all())
        assert transfer_type is not None and transfer_type.active is True
        assert buyer_role is not None and buyer_role.active is True
        assert buyer_role.name == 'خریدار / منتقل‌الیه مورد تأیید'
        assert project_type is not None and project_type.enabled is True
        assert states == {'DRAFT', 'IN_PROGRESS', 'READY_FOR_FINALIZATION'}
