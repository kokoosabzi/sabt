from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import (
    ParentContract, Permission, Person, Project, ProjectAccess, ProjectPerson,
    Role, RolePermission, User, UserRole,
)
from app.main import app


def import_api_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="import-tester", password_hash="unused", display_name="Import Tester",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="IMPORT", contract_code="76", name="Import Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    person = Person(first_name="Initial", last_name="Owner", created_at=now, updated_at=now,
                    version=1, is_active=True)
    role = Role(code="import-admin", name="Import Admin", active=True)
    permission = Permission(code="parent_contract.create", name="Create Parent Contract")
    db.add_all([user, project, person, role, permission])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
        ProjectPerson(project_id=project.id, person_id=person.id, active=True,
                      created_at=now, updated_at=now),
    ])
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: user
    client = TestClient(app)
    return engine, db, client, user, project, person


def close_import_api_context(context):
    engine, db, *_ = context
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_contract_import_preview_and_confirmation_are_transactional():
    context = import_api_context()
    engine, db, client, user, project, person = context
    try:
        response = client.post(
            f"/contracts/parent/import/preview?project_id={project.id}",
            files={"file": ("contracts.csv", f"suffix,initial_person_id,property_id\n0123,{person.id},\n".encode(), "text/csv")},
        )
        assert response.status_code == 200
        preview = response.json()
        assert preview["can_confirm"] is True
        assert preview["rows"][0]["contract_number"] == "760123"
        assert db.scalar(select(ParentContract.id)) is None

        confirmed = client.post(
            "/contracts/parent/import/confirm",
            json={"project_id": project.id, "rows": preview["rows"]},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["created_count"] == 1
        assert confirmed.json()["contracts"][0]["contract_number"] == "760123"
        assert db.scalar(select(ParentContract.contract_number)) == "760123"
    finally:
        close_import_api_context(context)


def test_contract_import_preview_reports_duplicate_rows_without_writes():
    context = import_api_context()
    engine, db, client, user, project, person = context
    try:
        content = f"suffix,initial_person_id\n0123,{person.id}\n0123,{person.id}\n".encode()
        response = client.post(
            f"/contracts/parent/import/preview?project_id={project.id}",
            files={"file": ("contracts.csv", content, "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["can_confirm"] is False
        assert body["invalid_count"] == 2
        assert all("duplicate_suffix_in_file" in row["issues"] for row in body["rows"])
        assert db.scalar(select(ParentContract.id)) is None
    finally:
        close_import_api_context(context)


def test_contract_import_requires_create_permission():
    context = import_api_context()
    engine, db, client, user, project, person = context
    try:
        db.query(RolePermission).delete()
        db.commit()
        response = client.post(
            f"/contracts/parent/import/preview?project_id={project.id}",
            files={"file": ("contracts.csv", f"suffix,initial_person_id\n0123,{person.id}\n".encode(), "text/csv")},
        )
        assert response.status_code == 403
    finally:
        close_import_api_context(context)
