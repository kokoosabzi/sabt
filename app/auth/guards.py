from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.authorization import AuthorizationContext, authorize
from app.auth.dependencies import current_user, get_db

def require_permission(permission_code: str, project_id: int | None = None):
    def dependency(user=Depends(current_user), db: Session = Depends(get_db)):
        try:
            authorize(db, user, permission_code, AuthorizationContext(project_id=project_id))
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden')
        return user
    return dependency