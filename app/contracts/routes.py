from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Person, Project, ProjectPerson, ProjectProperty, Property
from app.contracts.service import (
    ParentContractConflictError,
    ParentContractNotFoundError,
    ParentContractValidationError,
    create_parent_contract,
    get_parent_contract_history,
)

router = APIRouter(prefix="/contracts/parent", tags=["contracts"])


@router.get("/options")
def parent_contract_options(
    project_id: int,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return active people and properties associated with an authorized project."""
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(
            db, user, "parent_contract.create",
            AuthorizationContext(project_id=project_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    people = db.execute(
        select(Person)
        .join(
            ProjectPerson,
            (ProjectPerson.person_id == Person.id)
            & (ProjectPerson.project_id == project_id),
        )
        .where(Person.is_active.is_(True), ProjectPerson.active.is_(True))
        .order_by(Person.last_name, Person.first_name, Person.id)
    ).scalars().all()
    properties = db.execute(
        select(Property)
        .join(
            ProjectProperty,
            (ProjectProperty.property_id == Property.id)
            & (ProjectProperty.project_id == project_id),
        )
        .where(Property.is_active.is_(True), ProjectProperty.active.is_(True))
        .order_by(
            Property.block_tower, Property.floor,
            Property.unit_number, Property.id,
        )
    ).scalars().all()
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "contract_code": project.contract_code,
        },
        "people": [
            {
                "id": person.id,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "national_id": person.national_id,
                "mobile": person.mobile,
            }
            for person in people
        ],
        "properties": [
            {
                "id": prop.id,
                "block_tower": prop.block_tower,
                "floor": prop.floor,
                "unit_number": prop.unit_number,
                "unit_code": prop.unit_code,
                "plaque_number": prop.plaque_number,
            }
            for prop in properties
        ],
    }


class ParentContractCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    project_id: int = Field(ge=1)
    suffix: str = Field(min_length=4, max_length=4, pattern=r"^[0-9]{4}$")
    initial_person_id: int = Field(ge=1)
    property_id: int | None = Field(default=None, ge=1)


@router.post("", status_code=201)
def create_parent_contract_endpoint(
    payload: ParentContractCreateRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a stable Parent Contract root using the project contract code."""
    try:
        record = create_parent_contract(
            db, user, payload.project_id, payload.suffix,
            payload.initial_person_id, payload.property_id,
        )
        db.commit()
        db.refresh(record)
    except ParentContractNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ParentContractConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ParentContractValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "id": record.id,
        "project_id": record.project_id,
        "contract_number": record.contract_number,
        "suffix": record.suffix,
        "initial_person_id": record.initial_person_id,
        "property_id": record.property_id,
        "status": record.status,
        "next_transfer_sequence": record.next_transfer_sequence,
        "version": record.version,
    }


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
