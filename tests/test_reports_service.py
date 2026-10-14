from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.authorization import AuthorizationContext, authorize
from app.db.base import Base
from app.db.models import (
    Operation, OperationType, Permission, Project, ProjectAccess, Role, RolePermission,
    User, UserRole,
)
from app.reports.service import ReportValidationError, get_management_summary, get_workflow_report


@pytest.fixture()
def report_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    now = datetime.now(timezone.utc)
    user = User(username="report-tester", password_hash="unused", display_name="Report Tester",
                active=True, created_at=now, updated_at=now, version=1)
    project = Project(code="REPORT-P", name="Report Project", status="ACTIVE",
                      timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    role = Role(code="report-viewer", name="Report Viewer", active=True)
    summary_permission = Permission(code="management_dashboard.view", name="Dashboard")
    workflow_permission = Permission(code="workflow_report.view", name="Workflow Report")
    operation_type = OperationType(code="TRANSFER", name="Transfer", active=True, system_defined=False,
                                   created_at=now, updated_at=now)
    db.add_all([user, project, role, summary_permission, workflow_permission, operation_type])
    db.flush()
    db.add_all([
        RolePermission(role_id=role.id, permission_id=summary_permission.id),
        RolePermission(role_id=role.id, permission_id=workflow_permission.id),
        UserRole(user_id=user.id, role_id=role.id, project_id=None),
        ProjectAccess(user_id=user.id, project_id=project.id, active=True, granted_at=now, version=1),
    ])
    op = Operation(project_id=project.id, operation_type_id=operation_type.id, status="DRAFT",
                   current_workflow_state="DRAFT", created_by=user.id, created_at=now,
                   updated_at=now, version=1, current_version_number=0)
    finalized = Operation(project_id=project.id, operation_type_id=operation_type.id, status="FINALIZED",
                          current_workflow_state="FINALIZED", created_by=user.id, finalized_by=user.id,
                          created_at=now - timedelta(days=1), updated_at=now,
                          finalized_at=now, version=2, current_version_number=1)
    db.add_all([op, finalized])
    db.commit()
    try:
        yield db, user, project, now, op, finalized
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_management_summary_counts_created_and_finalized_by_their_own_timestamps(report_context):
    db, user, project, now, _, _ = report_context
    result = get_management_summary(db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1))
    assert result["indicators"]["created_operations"] == 1
    assert result["indicators"]["finalized_operations"] == 1
    assert result["indicators"]["currently_open_operations"] == 1
    assert result["indicators"]["created_operations_by_status"] == [{"status": "DRAFT", "count": 1}]


def test_workflow_report_is_project_scoped_and_paginated(report_context):
    db, user, project, now, op, _ = report_context
    result = get_workflow_report(db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1), limit=1)
    assert result["pagination"] == {"limit": 1, "offset": 0, "total": 1}
    assert result["items"][0]["operation_id"] == op.id
    assert result["period"]["basis"] == "operation.created_at"


def test_reporting_requires_project_permission(report_context):
    db, user, project, now, _, _ = report_context
    db.query(RolePermission).delete()
    db.commit()
    with pytest.raises(PermissionError, match="forbidden"):
        get_management_summary(db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1))


def test_reporting_rejects_invalid_time_range(report_context):
    db, user, project, now, _, _ = report_context
    with pytest.raises(ReportValidationError, match="report_range_invalid"):
        get_management_summary(db, user, project.id, now, now)


def test_reporting_routes_are_registered():
    from app.main import app
    paths = set(app.openapi()['paths'])
    assert '/reports/management-summary' in paths
    assert '/reports/workflow' in paths



def test_report_rejects_naive_datetimes(report_context):
    db, user, project, now, _, _ = report_context
    with pytest.raises(ReportValidationError, match="report_start_must_include_timezone"):
        get_management_summary(db, user, project.id, now.replace(tzinfo=None), now + timedelta(hours=1))


def test_workflow_report_supports_status_and_creator_filters(report_context):
    db, user, project, now, op, _ = report_context
    result = get_workflow_report(
        db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1),
        status="DRAFT", created_by=user.id, limit=10, offset=0,
    )
    assert result["pagination"]["total"] == 1
    assert result["items"][0]["operation_id"] == op.id
    assert result["items"][0]["created_by_display_name"] == user.display_name
    assert result["filters"]["created_by"] == user.id


def test_workflow_report_rejects_malformed_contract_filters(report_context):
    db, user, project, now, _, _ = report_context
    with pytest.raises(ReportValidationError, match="parent_contract_number_invalid"):
        get_workflow_report(
            db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1),
            parent_contract_number="76X123",
        )
    with pytest.raises(ReportValidationError, match="child_contract_number_invalid"):
        get_workflow_report(
            db, user, project.id, now - timedelta(hours=1), now + timedelta(hours=1),
            child_contract_number="760123",
        )


def test_cross_project_report_access_denied(report_context):
    db, user, project, now, _, _ = report_context
    other = Project(code="OTHER-REPORT-P", name="Other Project", status="ACTIVE",
                    timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
    db.add(other)
    db.commit()
    with pytest.raises(PermissionError, match="forbidden"):
        get_management_summary(db, user, other.id, now - timedelta(hours=1), now + timedelta(hours=1))
