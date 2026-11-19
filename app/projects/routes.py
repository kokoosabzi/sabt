from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.db.models import User
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
        return validate_project_timezone(value)


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
