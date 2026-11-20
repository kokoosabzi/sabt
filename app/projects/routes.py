from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import OperationType, OperationTypeWorkflow, PartyRole, Project, ProjectOperationType, User
from app.projects.service import (
    ProjectConflictError,
    ProjectValidationError,
    create_project,
    list_accessible_projects,
    validate_project_timezone,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    contract_code: str = Field(pattern=r"^[1-9][0-9]$")
    description: str | None = Field(default=None, max_length=4000)
    timezone: str = Field(default="Asia/Tehran", min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        try:
            return validate_project_timezone(value)
        except ProjectValidationError as exc:
            raise ValueError("project_timezone_invalid") from exc


@router.post("", status_code=201)
def create_project_endpoint(
    payload: ProjectCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a project and grant the creator active access atomically."""
    try:
        project = create_project(
            db,
            user,
            code=payload.code,
            name=payload.name,
            contract_code=payload.contract_code,
            description=payload.description,
            timezone_name=payload.timezone,
        )
        db.commit()
        db.refresh(project)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except ProjectConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProjectValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "id": project.id,
        "code": project.code,
        "contract_code": project.contract_code,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "timezone": project.timezone,
        "version": project.version,
    }


@router.get("")
def list_projects_endpoint(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    projects = list_accessible_projects(db, user)
    return {
        "items": [
            {
                "id": project.id,
                "code": project.code,
                "contract_code": project.contract_code,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "timezone": project.timezone,
                "version": project.version,
            }
            for project in projects
        ],
        "total": len(projects),
    }

@router.get("/{project_id}/operation-types")
def list_project_operation_types_endpoint(
    project_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(db, user, "operation.view", AuthorizationContext(project_id=project_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    items = db.scalars(select(OperationType).join(
        ProjectOperationType, ProjectOperationType.operation_type_id == OperationType.id,
    ).where(
        ProjectOperationType.project_id == project_id,
        ProjectOperationType.enabled.is_(True),
        OperationType.active.is_(True),
        OperationType.retired_at.is_(None),
    ).order_by(OperationType.name, OperationType.id)).all()
    return {"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]}



@router.get("/{project_id}/operation-types/{operation_type_id}/workflow-states")
def list_project_operation_workflow_states_endpoint(
    project_id: int,
    operation_type_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the effective ordered workflow for an enabled project operation type."""
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(db, user, "operation.view", AuthorizationContext(project_id=project_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc

    enabled = db.scalar(select(ProjectOperationType.id).where(
        ProjectOperationType.project_id == project_id,
        ProjectOperationType.operation_type_id == operation_type_id,
        ProjectOperationType.enabled.is_(True),
    ))
    if enabled is None:
        raise HTTPException(status_code=404, detail="project_operation_type_not_found")

    states = db.scalars(
        select(OperationTypeWorkflow)
        .where(
            OperationTypeWorkflow.project_id == project_id,
            OperationTypeWorkflow.operation_type_id == operation_type_id,
            OperationTypeWorkflow.active.is_(True),
        )
        .order_by(OperationTypeWorkflow.sequence_no, OperationTypeWorkflow.id)
    ).all()
    source = "project"
    if not states:
        states = db.scalars(
            select(OperationTypeWorkflow)
            .where(
                OperationTypeWorkflow.project_id.is_(None),
                OperationTypeWorkflow.operation_type_id == operation_type_id,
                OperationTypeWorkflow.active.is_(True),
            )
            .order_by(OperationTypeWorkflow.sequence_no, OperationTypeWorkflow.id)
        ).all()
        source = "global"
    codes = [state.state_code for state in states]
    sequences = [state.sequence_no for state in states]
    valid = (
        len(codes) == len(set(codes))
        and len(sequences) == len(set(sequences))
        and "DRAFT" in codes
        and "READY_FOR_FINALIZATION" in codes
        and "FINALIZED" not in codes
    )
    return {
        "project_id": project_id,
        "operation_type_id": operation_type_id,
        "source": source,
        "valid": valid,
        "items": [
            {"state_code": state.state_code, "sequence_no": state.sequence_no}
            for state in states
        ],
    }


@router.get("/{project_id}/party-roles")
def list_project_party_roles_endpoint(
    project_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List active party roles for an authorized project operation workspace."""
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(db, user, "operation.view", AuthorizationContext(project_id=project_id))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    items = db.scalars(
        select(PartyRole)
        .where(PartyRole.active.is_(True), PartyRole.retired_at.is_(None))
        .order_by(PartyRole.name, PartyRole.id)
    ).all()
    return {"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]}
