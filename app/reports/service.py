from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.authorization import AuthorizationContext, authorize, has_permission
from app.contracts.numbering import validate_parent_contract_number
from app.db.models import Operation, OperationType, ParentContract, Project, User, WorkflowEvent


class ReportValidationError(ValueError):
    pass


def _authorize_project_report(db: Session, user: User, project_id: int, permission: str) -> Project:
    # Check access before resolving the project to avoid exposing whether an
    # inaccessible project ID exists.
    authorize(db, user, permission, AuthorizationContext(project_id=project_id))
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project_not_found")
    return project


def _validate_range(start_at: datetime, end_at: datetime) -> tuple[datetime, datetime]:
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ReportValidationError("report_start_must_include_timezone")
    if end_at.tzinfo is None or end_at.utcoffset() is None:
        raise ReportValidationError("report_end_must_include_timezone")
    start = start_at.astimezone(timezone.utc)
    end = end_at.astimezone(timezone.utc)
    if start >= end:
        raise ReportValidationError("report_range_invalid")
    return start, end


def get_management_summary(
    db: Session,
    user: User,
    project_id: int,
    start_at: datetime,
    end_at: datetime,
) -> dict:
    """Calculate dashboard indicators from persisted records only.

    Creation metrics use Operation.created_at; completion metrics use
    Operation.finalized_at. No historical state transitions or time-in-state
    are inferred because those events are not currently persisted.
    """
    start_at, end_at = _validate_range(start_at, end_at)
    project = _authorize_project_report(db, user, project_id, "management_dashboard.view")

    base = select(Operation).where(Operation.project_id == project_id)
    created_range = base.where(Operation.created_at >= start_at, Operation.created_at < end_at)
    finalized_range = base.where(
        Operation.status == "FINALIZED",
        Operation.finalized_at.is_not(None),
        Operation.finalized_at >= start_at,
        Operation.finalized_at < end_at,
    )
    created_count = db.scalar(select(func.count()).select_from(created_range.subquery())) or 0
    finalized_count = db.scalar(select(func.count()).select_from(finalized_range.subquery())) or 0

    currently_open_operations = db.scalar(
        select(func.count(Operation.id)).where(
            Operation.project_id == project_id,
            Operation.status.not_in(("FINALIZED", "CANCELLED", "REJECTED")),
        )
    ) or 0

    status_rows = db.execute(
        select(Operation.status, func.count(Operation.id))
        .where(
            Operation.project_id == project_id,
            Operation.created_at >= start_at,
            Operation.created_at < end_at,
        )
        .group_by(Operation.status)
        .order_by(Operation.status)
    ).all()

    parent_contracts_created = db.scalar(
        select(func.count(ParentContract.id)).where(
            ParentContract.project_id == project_id,
            ParentContract.created_at >= start_at,
            ParentContract.created_at < end_at,
        )
    ) or 0
    transfers_finalized = db.scalar(
        select(func.count(Operation.id)).where(
            Operation.project_id == project_id,
            Operation.parent_contract_id.is_not(None),
            Operation.status == "FINALIZED",
            Operation.finalized_at.is_not(None),
            Operation.finalized_at >= start_at,
            Operation.finalized_at < end_at,
        )
    ) or 0

    return {
        "project": {
            "id": project.id, "code": project.code, "name": project.name,
            "timezone": project.timezone,
        },
        "period": {
            "start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
            "range_semantics": "[start_at, end_at)",
        },
        "indicators": {
            "created_operations": created_count,
            "finalized_operations": finalized_count,
            "currently_open_operations": currently_open_operations,
            "created_operations_by_status": [
                {"status": status, "count": count} for status, count in status_rows
            ],
            "parent_contracts_created": parent_contracts_created,
            "transfers_finalized": transfers_finalized,
        },
        "data_notes": [
            "created_operations is based on operations.created_at",
            "finalized_operations is based on finalized_at and FINALIZED status",
            "parent_contracts_created is based on parent_contracts.created_at",
            "transfers_finalized counts finalized operations linked to a Parent Contract",
            "historical state transitions and time-in-state are not available from current records",
            "input timestamps must include a UTC offset; query bounds are normalized to UTC",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by_user_id": user.id,
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
    parent_contract_number: str | None = None,
    child_contract_number: str | None = None,
    property_id: int | None = None,
    created_by: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return a stable, project-scoped, paginated workflow report."""
    start_at, end_at = _validate_range(start_at, end_at)
    project = _authorize_project_report(db, user, project_id, "workflow_report.view")
    if limit < 1 or limit > 100:
        raise ReportValidationError("report_limit_invalid")
    if offset < 0:
        raise ReportValidationError("report_offset_invalid")
    if parent_contract_number is not None:
        try:
            validate_parent_contract_number(parent_contract_number)
        except ValueError as exc:
            raise ReportValidationError("parent_contract_number_invalid") from exc
    if child_contract_number is not None:
        try:
            parent_number, sequence_text = child_contract_number.split("/", 1)
            validate_parent_contract_number(parent_number)
            if not sequence_text.isdigit() or int(sequence_text) < 1 or str(int(sequence_text)) != sequence_text:
                raise ValueError("transfer_sequence_invalid")
        except ValueError as exc:
            raise ReportValidationError("child_contract_number_invalid") from exc

    stmt = (
        select(Operation, OperationType.name, ParentContract.contract_number, User.display_name)
        .join(OperationType, OperationType.id == Operation.operation_type_id)
        .join(User, User.id == Operation.created_by)
        .outerjoin(ParentContract, (ParentContract.id == Operation.parent_contract_id) & (ParentContract.project_id == Operation.project_id))
        .where(
            Operation.project_id == project_id,
            Operation.created_at >= start_at,
            Operation.created_at < end_at,
        )
    )
    count_stmt = (
        select(func.count(Operation.id))
        .select_from(Operation)
        .outerjoin(ParentContract, (ParentContract.id == Operation.parent_contract_id) & (ParentContract.project_id == Operation.project_id))
        .where(
            Operation.project_id == project_id,
            Operation.created_at >= start_at,
            Operation.created_at < end_at,
        )
    )
    filters = []
    if status:
        filters.append(Operation.status == status)
    if operation_type_id is not None:
        filters.append(Operation.operation_type_id == operation_type_id)
    if parent_contract_number is not None:
        filters.append(ParentContract.contract_number == parent_contract_number)
    if child_contract_number is not None:
        filters.append(Operation.child_contract_number == child_contract_number)
    if property_id is not None:
        filters.append(Operation.property_id == property_id)
    if created_by is not None:
        filters.append(Operation.created_by == created_by)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = db.execute(
        stmt.order_by(Operation.created_at.desc(), Operation.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {
        "project": {
            "id": project.id, "code": project.code, "name": project.name,
            "timezone": project.timezone,
        },
        "period": {
            "start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
            "basis": "operation.created_at", "range_semantics": "[start_at, end_at)",
        },
        "filters": {
            "status": status, "operation_type_id": operation_type_id,
            "parent_contract_number": parent_contract_number,
            "child_contract_number": child_contract_number,
            "property_id": property_id, "created_by": created_by,
        },
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
                "created_by_display_name": creator_name,
                "created_at": op.created_at.isoformat(),
                "updated_at": op.updated_at.isoformat(),
                "finalized_at": op.finalized_at.isoformat() if op.finalized_at else None,
                "parent_contract_id": op.parent_contract_id,
                "parent_contract_number": parent_number,
                "transfer_sequence": op.transfer_sequence,
                "child_contract_number": op.child_contract_number,
                "current_version_number": op.current_version_number,
            }
            for op, type_name, parent_number, creator_name in rows
        ],
    }



def get_workflow_events_report(
    db: Session,
    user: User,
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    *,
    event_type: str | None = None,
    operation_id: int | None = None,
    actor_user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return actual recorded workflow/activity events for a project and time range."""
    start_at, end_at = _validate_range(start_at, end_at)
    project = _authorize_project_report(db, user, project_id, "workflow_report.view")
    if limit < 1 or limit > 100:
        raise ReportValidationError("report_limit_invalid")
    if offset < 0:
        raise ReportValidationError("report_offset_invalid")
    if operation_id is not None and operation_id < 1:
        raise ReportValidationError("operation_id_invalid")
    if actor_user_id is not None and actor_user_id < 1:
        raise ReportValidationError("actor_user_id_invalid")

    filters = [
        WorkflowEvent.project_id == project_id,
        WorkflowEvent.occurred_at >= start_at,
        WorkflowEvent.occurred_at < end_at,
    ]
    if event_type:
        filters.append(WorkflowEvent.event_type == event_type)
    if operation_id is not None:
        filters.append(WorkflowEvent.operation_id == operation_id)
    if actor_user_id is not None:
        filters.append(WorkflowEvent.actor_user_id == actor_user_id)

    count_stmt = (
        select(func.count(WorkflowEvent.id))
        .join(Operation, Operation.id == WorkflowEvent.operation_id)
        .where(*filters, Operation.project_id == project_id)
    )
    stmt = (
        select(WorkflowEvent, OperationType.name, User.display_name, Operation.child_contract_number,
               ParentContract.contract_number)
        .join(Operation, Operation.id == WorkflowEvent.operation_id)
        .join(OperationType, OperationType.id == Operation.operation_type_id)
        .join(User, User.id == WorkflowEvent.actor_user_id)
        .outerjoin(ParentContract, (ParentContract.id == Operation.parent_contract_id) & (ParentContract.project_id == Operation.project_id))
        .where(*filters, Operation.project_id == project_id)
    )
    total = db.scalar(count_stmt) or 0
    rows = db.execute(
        stmt.order_by(WorkflowEvent.occurred_at.desc(), WorkflowEvent.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {
        "project": {"id": project.id, "code": project.code, "name": project.name,
                    "timezone": project.timezone},
        "period": {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
                   "basis": "workflow_events.occurred_at", "range_semantics": "[start_at, end_at)"},
        "filters": {"event_type": event_type, "operation_id": operation_id,
                    "actor_user_id": actor_user_id},
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "items": [
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "operation_id": event.operation_id,
                "operation_type_name": operation_type_name,
                "parent_contract_number": parent_number,
                "child_contract_number": child_number,
                "actor_user_id": event.actor_user_id,
                "actor_display_name": actor_name,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "occurred_at": event.occurred_at.isoformat(),
                "metadata": json.loads(event.metadata_json) if event.metadata_json else {},
            }
            for event, operation_type_name, actor_name, child_number, parent_number in rows
        ],
    }


def get_report_project_context(db: Session, user: User, project_id: int) -> dict:
    """Return project display/timezone context only when the user can view reports."""
    if project_id < 1:
        raise ReportValidationError("project_id_invalid")
    permitted = (
        has_permission(db, user, "management_dashboard.view", project_id)
        or has_permission(db, user, "workflow_report.view", project_id)
    )
    if not permitted:
        raise PermissionError("forbidden")
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project_not_found")
    try:
        ZoneInfo(project.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ReportValidationError("project_timezone_invalid") from exc
    return {
        "project": {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "timezone": project.timezone,
        }
    }
