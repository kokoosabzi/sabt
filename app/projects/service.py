from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.authorization import authorize
from app.db.models import Project, ProjectAccess, User


class ProjectError(Exception):
    pass


class ProjectConflictError(ProjectError):
    pass


class ProjectValidationError(ProjectError):
    pass


def validate_project_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ProjectValidationError("project_timezone_invalid") from exc
    return value


def create_project(
    db: Session,
    user: User,
    *,
    code: str,
    name: str,
    contract_code: str | None = None,
    description: str | None = None,
    timezone_name: str = "Asia/Tehran",
) -> Project:
    """Create a project and grant its creator active access in the caller transaction."""
    authorize(db, user, "project.create")
    normalized_code = code.strip().lower()
    normalized_name = name.strip()
    normalized_contract_code = contract_code.strip() if contract_code else None
    if not normalized_code or len(normalized_code) > 64:
        raise ProjectValidationError("project_code_invalid")
    if not normalized_name or len(normalized_name) > 200:
        raise ProjectValidationError("project_name_invalid")
    if normalized_contract_code is not None and (
        len(normalized_contract_code) != 2
        or not normalized_contract_code.isascii()
        or not normalized_contract_code.isdigit()
        or normalized_contract_code[0] == "0"
    ):
        raise ProjectValidationError("project_contract_code_invalid")
    validate_project_timezone(timezone_name)

    if db.scalar(select(Project.id).where(Project.code == normalized_code)) is not None:
        raise ProjectConflictError("project_code_exists")
    if normalized_contract_code is not None and db.scalar(
        select(Project.id).where(Project.contract_code == normalized_contract_code)
    ) is not None:
        raise ProjectConflictError("project_contract_code_exists")

    now = datetime.now(timezone.utc)
    project = Project(
        code=normalized_code,
        contract_code=normalized_contract_code,
        name=normalized_name,
        description=description.strip() if description and description.strip() else None,
        status="ACTIVE",
        timezone=timezone_name,
        created_at=now,
        updated_at=now,
        version=1,
    )
    db.add(project)
    db.flush()
    db.add(
        ProjectAccess(
            user_id=user.id,
            project_id=project.id,
            active=True,
            granted_by=user.id,
            granted_at=now,
            revoked_at=None,
            version=1,
        )
    )
    db.flush()
    return project


def list_accessible_projects(db: Session, user: User) -> list[Project]:
    """Return only active project memberships the caller can view."""
    rows = db.scalars(
        select(Project)
        .join(ProjectAccess, ProjectAccess.project_id == Project.id)
        .where(ProjectAccess.user_id == user.id, ProjectAccess.active.is_(True))
        .order_by(Project.name, Project.id)
    ).all()
    visible: list[Project] = []
    for project in rows:
        try:
            authorize(
                db,
                user,
                "project.view",
                __import__("app.auth.authorization", fromlist=["AuthorizationContext"]).AuthorizationContext(
                    project_id=project.id
                ),
            )
        except PermissionError:
            continue
        visible.append(project)
    return visible
