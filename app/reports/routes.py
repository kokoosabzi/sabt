from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.reports.service import ReportValidationError, get_management_summary, get_workflow_events_report, get_workflow_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_response(fn):
    try:
        return fn()
    except ReportValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/management/summary")
def management_summary(
    project_id: int = Query(..., ge=1),
    start_at: datetime = Query(...),
    end_at: datetime = Query(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return _report_response(lambda: get_management_summary(db, user, project_id, start_at, end_at))


@router.get("/workflow")
def workflow_report(
    project_id: int = Query(..., ge=1),
    start_at: datetime = Query(...),
    end_at: datetime = Query(...),
    status: str | None = Query(None, min_length=1, max_length=32),
    operation_type_id: int | None = Query(None, ge=1),
    parent_contract_number: str | None = Query(None, min_length=6, max_length=6),
    child_contract_number: str | None = Query(None, min_length=8, max_length=32),
    property_id: int | None = Query(None, ge=1),
    created_by: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return _report_response(lambda: get_workflow_report(
        db, user, project_id, start_at, end_at,
        status=status,
        operation_type_id=operation_type_id,
        parent_contract_number=parent_contract_number,
        child_contract_number=child_contract_number,
        property_id=property_id,
        created_by=created_by,
        limit=limit,
        offset=offset,
    ))


@router.get("/workflow/events")
def workflow_events_report(
    project_id: int,
    start_at: datetime = Query(...),
    end_at: datetime = Query(...),
    event_type: str | None = Query(None, min_length=1, max_length=64),
    operation_id: int | None = Query(None, ge=1),
    actor_user_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return _report_response(lambda: get_workflow_events_report(
        db, user, project_id, start_at, end_at,
        event_type=event_type, operation_id=operation_id,
        actor_user_id=actor_user_id, limit=limit, offset=offset,
    ))
