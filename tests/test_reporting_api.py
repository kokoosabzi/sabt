from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import current_user, get_db
from app.db.base import Base
from app.db.models import Permission, Project, ProjectAccess, Role, RolePermission, User, UserRole
from app.main import app


def _context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="report-user", password_hash="unused", display_name="Report User",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="REPORT-P", contract_code="77", name="Report Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    role = Role(code="report-viewer", name="Report Viewer", active=True)
    permissions = [
        Permission(code="management_dashboard.view", name="Management Dashboard"),
        Permission(code="workflow_report.view", name="Workflow Report"),
    ]
    db.add_all([user, project, role, *permissions])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=p.id) for p in permissions
    ])
    db.add(UserRole(user_id=user.id, role_id=role.id, project_id=None))
    db.add(ProjectAccess(user_id=user.id, project_id=project.id, active=True,
                         granted_at=now, version=1))
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[current_user] = lambda: user
    return engine, db, TestClient(app), project


def test_management_summary_api_returns_verified_empty_metrics():
    engine, db, client, project = _context()
    try:
        response = client.get("/reports/management/summary", params={
            "project_id": project.id,
            "start_at": "2026-10-01T00:00:00+00:00",
            "end_at": "2026-11-01T00:00:00+00:00",
        })
        assert response.status_code == 200
        body = response.json()
        assert body["project"]["id"] == project.id
        assert body["indicators"]["created_operations"] == 0
        assert body["indicators"]["finalized_operations"] == 0
        assert body["period"]["range_semantics"] == "[start_at, end_at)"
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_workflow_report_api_returns_paginated_empty_rows():
    engine, db, client, project = _context()
    try:
        response = client.get("/reports/workflow", params={
            "project_id": project.id,
            "start_at": "2026-10-01T00:00:00+00:00",
            "end_at": "2026-11-01T00:00:00+00:00",
            "limit": 10,
            "offset": 0,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["pagination"] == {"limit": 10, "offset": 0, "total": 0}
        assert body["items"] == []
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_reporting_api_rejects_invalid_range():
    engine, db, client, project = _context()
    try:
        response = client.get("/reports/management/summary", params={
            "project_id": project.id,
            "start_at": "2026-11-01T00:00:00+00:00",
            "end_at": "2026-10-01T00:00:00+00:00",
        })
        assert response.status_code == 422
        assert response.json()["detail"] == "report_range_invalid"
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_reporting_api_enforces_project_access():
    engine, db, client, project = _context()
    try:
        db.query(ProjectAccess).delete()
        db.commit()
        response = client.get("/reports/management/summary", params={
            "project_id": project.id,
            "start_at": "2026-10-01T00:00:00+00:00",
            "end_at": "2026-11-01T00:00:00+00:00",
        })
        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
