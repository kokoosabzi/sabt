from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.auth.service import authenticate, create_session, get_user_by_token, revoke_session
from app.contracts.routes import router as contracts_router
from app.contracts.import_routes import router as contract_import_router
from app.reports.routes import router as reports_router
from app.operations.routes import router as operations_router
from app.reports.service import get_management_summary

app = FastAPI(title="SABT", version="0.1.0")
app.mount("/portal", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="portal")
app.include_router(contracts_router)
app.include_router(contract_import_router)
app.include_router(reports_router)
app.include_router(operations_router)
basic = HTTPBasic()
bearer = HTTPBearer(auto_error=False)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", tags=["auth"])
def login(credentials: HTTPBasicCredentials = Depends(basic), db: Session = Depends(get_db)):
    user = authenticate(db, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_session(db, user), "token_type": "bearer", "expires_in": 28800}


@app.post("/auth/logout", tags=["auth"])
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    if get_user_by_token(db, credentials.credentials) is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    revoke_session(db, credentials.credentials)
    return {"status": "ok"}


@app.get("/auth/me", tags=["auth"])
def me(user=Depends(current_user)):
    return {"id": user.id, "username": user.username, "display_name": user.display_name}


@app.get("/reports/management-summary", tags=["reports"], deprecated=True)
def management_summary_legacy(
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Compatibility alias; new clients should use /reports/management/summary."""
    try:
        return get_management_summary(db, user, project_id, start_at, end_at)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
