from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import current_user, get_db
from app.reports.service import get_management_summary, get_workflow_report

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/management-summary")
def management_summary(project_id: int, start_at: datetime, end_at: datetime,
                       user=Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return get_management_summary(db, user, project_id, start_at, end_at)

@router.get("/workflow")
def workflow_report(project_id: int, start_at: datetime, end_at: datetime,
                    status: str | None = None, operation_type_id: int | None = None,
                    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
                    user=Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return get_workflow_report(db, user, project_id, start_at, end_at,
        status=status, operation_type_id=operation_type_id, limit=limit, offset=offset)
