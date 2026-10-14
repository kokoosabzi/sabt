from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Operation, OperationType, Project, User


class ReportValidationError(ValueError):
    pass


def _authorize_project_report(db: Session, user: User, project_id: int, permission: str) -> Project:
    authorize(db, user, permission, AuthorizationContext(project_id=project_id))
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project_not_found")
    return project


def _validate_range(start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise ReportValidationError("report_range_invalid")


def get_management_summary(
    db: Session,
    user: User,
    project_id: int,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    """Calculate dashboard indicators from existing operation records only.

    Created counts use Operation.created_at; finalized counts use finalized_at.
    This first version intentionally does not claim to measure historical state
    transitions or time-in-state because those events are not currently stored.
    """
    _validate_range(start_at, end_at)
    project = _authorize_project_report(db, user, project_id, "management_dashboard.view")

    base = select(Operation).where(Operation.project_id == project_id)
    created_range = base.where(Operation.created_at >= start_at, Operation.created_at < end_at)
    finalized_range = base.where(
        Operation.finalized_at.is_not(None),
        Operation.finalized_at >= start_at,
        Operation.finalized_at < end_at,
    )
    created_count = db.scalar(select(func.count()).select_from(created_range.subquery())) or 0
    finalized_count = db.scalar(select(func.count()).select_from(finalized_range.subquery())) or 0

    status_rows = db.execute(
        select(Operation.status, func.count(Operation.id))
        .where(Operation.project_id == project_id,
               Operation.created_at >= start_at, Operation.created_at < end_at)
        .group_by(Operation.status)
        .order_by(Operation.status)
    ).all()

    return {
        "project": {"id": project.id, "code": project.code, "name": project.name,
                    "timezone": project.timezone},
        "period": {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
                   "range_semantics": "[start_at, end_at)"},
        "indicators": {
            "created_operations": created_count,
            "finalized_operations": finalized_count,
            "created_operations_by_status": [
                {"status": status, "count": count} for status, count in status_rows
            ],
        },
        "data_notes": [
            "created_operations is based on operations.created_at",
            "finalized_operations is based on operations.finalized_at",
            "historical state transitions and time-in-state are not available from current records",
        ],
    }


def get_workflow_report(
    db: Session,
    user: User,
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    *,
    status: str | None = None,
    operation_type_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return a stable, project-scoped, paginated report by operation creation time."""
    _validate_range(start_at, end_at)
    project = _authorize_project_report(db, user, project_id, "workflow_report.view")
    if limit < 1 or limit > 100:
        raise ReportValidationError("report_limit_invalid")
    if offset < 0:
        raise ReportValidationError("report_offset_invalid")

    stmt = (
        select(Operation, OperationType.name)
        .join(OperationType, OperationType.id == Operation.operation_type_id)
        .where(
            Operation.project_id == project_id,
            Operation.created_at >= start_at,
            Operation.created_at < end_at,
        )
    )
    count_stmt = select(func.count(Operation.id)).where(
        Operation.project_id == project_id,
        Operation.created_at >= start_at,
        Operation.created_at < end_at,
    )
    if status:
        stmt = stmt.where(Operation.status == status)
        count_stmt = count_stmt.where(Operation.status == status)
    if operation_type_id is not None:
        stmt = stmt.where(Operation.operation_type_id == operation_type_id)
        count_stmt = count_stmt.where(Operation.operation_type_id == operation_type_id)

    total = db.scalar(count_stmt) or 0
    rows = db.execute(
        stmt.order_by(Operation.created_at.desc(), Operation.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {
        "project": {"id": project.id, "code": project.code, "name": project.name},
        "period": {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
                   "basis": "operation.created_at", "range_semantics": "[start_at, end_at)"},
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "items": [
            {
                "operation_id": op.id,
                "operation_type_id": op.operation_type_id,
                "operation_type_name": type_name,
                "status": op.status,
                "workflow_state": op.current_workflow_state,
                "property_id": op.property_id,
                "created_by": op.created_by,
                "created_at": op.created_at.isoformat(),
                "updated_at": op.updated_at.isoformat(),
                "finalized_at": op.finalized_at.isoformat() if op.finalized_at else None,
                "parent_contract_id": op.parent_contract_id,
                "transfer_sequence": op.transfer_sequence,
                "child_contract_number": op.child_contract_number,
            }
            for op, type_name in rows
        ],
    }
