from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.contracts.service import (
    ParentContractNotFoundError,
    ParentContractValidationError,
    get_parent_contract_history,
)

router = APIRouter(prefix="/contracts/parent", tags=["contracts"])


@router.get("/{contract_number}/history")
def parent_contract_history(
    contract_number: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authorized transfer chain and derived current owner."""
    try:
        return get_parent_contract_history(db, user, contract_number)
    except ParentContractValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ParentContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


from datetime import datetime
from sqlalchemy import func, select
from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Operation, OperationType, ParentContract, Project

reports_router = APIRouter(prefix="/reports", tags=["reports"])


def _report_context(db, user, project_id, start_at, end_at):
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="start_at_timezone_required")
    if end_at.tzinfo is None or end_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="end_at_timezone_required")
    if start_at >= end_at:
        raise HTTPException(status_code=422, detail="date_range_invalid")
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(db, user, "workflow.report.view", AuthorizationContext(project_id=project_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return project


@reports_router.get("/management-summary")
def management_summary(
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Summary metrics derived only from persisted operation and contract data."""
    project = _report_context(db, user, project_id, start_at, end_at)
    created = select(Operation).where(
        Operation.project_id == project_id,
        Operation.created_at >= start_at,
        Operation.created_at < end_at,
    ).subquery()
    status_rows = db.execute(
        select(created.c.status, func.count().label("count"))
        .group_by(created.c.status).order_by(created.c.status)
    ).all()
    created_count = db.scalar(select(func.count()).select_from(created)) or 0
    finalized_count = db.scalar(select(func.count()).select_from(Operation).where(
        Operation.project_id == project_id, Operation.status == "FINALIZED",
        Operation.finalized_at >= start_at, Operation.finalized_at < end_at,
    )) or 0
    open_count = db.scalar(select(func.count()).select_from(Operation).where(
        Operation.project_id == project_id,
        Operation.status.not_in(("FINALIZED", "CANCELLED", "REJECTED")),
    )) or 0
    parent_count = db.scalar(select(func.count()).select_from(ParentContract).where(
        ParentContract.project_id == project_id,
    )) or 0
    transfer_count = db.scalar(select(func.count()).select_from(Operation).where(
        Operation.project_id == project_id, Operation.parent_contract_id.is_not(None),
        Operation.status == "FINALIZED", Operation.finalized_at >= start_at,
        Operation.finalized_at < end_at,
    )) or 0
    return {
        "project": {"id": project.id, "code": project.code, "name": project.name, "timezone": project.timezone},
        "period": {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "end_exclusive": True,
                   "created_date_basis": "operation.created_at", "finalized_date_basis": "operation.finalized_at"},
        "metrics": {"operations_created_in_period": created_count, "operations_finalized_in_period": finalized_count,
                    "currently_open_operations": open_count, "parent_contracts_total": parent_count,
                    "transfers_finalized_in_period": transfer_count},
        "created_operations_by_status": [{"status": row.status, "count": row.count} for row in status_rows],
        "limitations": ["Uses persisted operation timestamps and current status only.",
                        "Does not reconstruct every workflow transition; an append-only workflow event log is not yet implemented."],
    }


@reports_router.get("/workflow-operations")
def workflow_operations_report(
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    status: str | None = None,
    operation_type_id: int | None = None,
    parent_contract_number: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Paginated operation report; date range is based on operation creation time."""
    _report_context(db, user, project_id, start_at, end_at)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit_out_of_range")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset_invalid")
    if parent_contract_number is not None and (
        len(parent_contract_number) != 6 or not parent_contract_number.isascii()
        or not parent_contract_number.isdigit()
    ):
        raise HTTPException(status_code=422, detail="parent_contract_number_invalid")

    conditions = [
        Operation.project_id == project_id,
        Operation.created_at >= start_at,
        Operation.created_at < end_at,
    ]
    if status is not None:
        conditions.append(Operation.status == status)
    if operation_type_id is not None:
        conditions.append(Operation.operation_type_id == operation_type_id)
    if parent_contract_number is not None:
        conditions.append(Operation.parent_contract_id == ParentContract.id)
        conditions.append(ParentContract.contract_number == parent_contract_number)

    query = select(Operation)
    count_query = select(func.count()).select_from(Operation)
    if parent_contract_number is not None:
        query = query.join(ParentContract, (ParentContract.id == Operation.parent_contract_id) & (ParentContract.project_id == Operation.project_id))
        count_query = count_query.join(ParentContract, (ParentContract.id == Operation.parent_contract_id) & (ParentContract.project_id == Operation.project_id))
    query = query.where(*conditions)
    count_query = count_query.where(*conditions)
    total = db.scalar(count_query) or 0
    rows = db.scalars(query.order_by(Operation.created_at.desc(), Operation.id.desc()).offset(offset).limit(limit)).all()
    type_ids = {row.operation_type_id for row in rows}
    type_names = {row.id: row.name for row in db.scalars(
        select(OperationType).where(OperationType.id.in_(type_ids))
    ).all()} if type_ids else {}
    return {
        "project_id": project_id,
        "period": {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(),
                   "end_exclusive": True, "date_basis": "operation.created_at"},
        "filters": {"status": status, "operation_type_id": operation_type_id,
                    "parent_contract_number": parent_contract_number},
        "pagination": {"limit": limit, "offset": offset, "total": total,
                       "has_more": offset + len(rows) < total},
        "items": [{
            "operation_id": row.id, "operation_type_id": row.operation_type_id,
            "operation_type_name": type_names.get(row.operation_type_id), "status": row.status,
            "workflow_state": row.current_workflow_state, "property_id": row.property_id,
            "created_by": row.created_by, "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "finalized_at": row.finalized_at.isoformat() if row.finalized_at else None,
            "parent_contract_id": row.parent_contract_id, "transfer_sequence": row.transfer_sequence,
            "child_contract_number": row.child_contract_number,
        } for row in rows],
        "limitations": ["Rows are filtered by operation creation time, not every workflow event.",
                        "Historical status transitions and time-in-state require an append-only workflow event log."],
    }
