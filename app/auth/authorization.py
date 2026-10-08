from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Permission, ProjectAccess, Role, RolePermission, User, UserRole

@dataclass(frozen=True)
class AuthorizationContext:
    project_id: int | None = None

def has_project_access(db: Session, user_id: int, project_id: int) -> bool:
    row = db.scalar(select(ProjectAccess).where(ProjectAccess.user_id == user_id, ProjectAccess.project_id == project_id, ProjectAccess.active.is_(True)))
    return row is not None

def has_permission(db: Session, user: User, permission_code: str, project_id: int | None = None) -> bool:
    stmt = (select(Permission.id).join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id, Permission.code == permission_code, Role.active.is_(True)))
    if project_id is not None:
        if not has_project_access(db, user.id, project_id):
            return False
        stmt = stmt.where((UserRole.project_id.is_(None)) | (UserRole.project_id == project_id))
    else:
        stmt = stmt.where(UserRole.project_id.is_(None))
    return db.scalar(stmt) is not None

def authorize(db: Session, user: User, permission_code: str, context: AuthorizationContext | None = None) -> None:
    if not user.active:
        raise PermissionError('inactive_user')
    project_id = context.project_id if context else None
    if not has_permission(db, user, permission_code, project_id):
        raise PermissionError('forbidden')