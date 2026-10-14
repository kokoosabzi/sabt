from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.auth.dependencies import current_user, get_db
from app.auth.service import authenticate, create_session, get_user_by_token, revoke_session
from app.contracts.routes import router as contracts_router
from app.reports.routes import router as reports_router
from app.reports.service import get_management_summary, get_workflow_report

app = FastAPI(title='SABT', version='0.1.0')
app.include_router(contracts_router)
app.include_router(reports_router)
basic = HTTPBasic()
bearer = HTTPBearer(auto_error=False)

@app.get('/health', tags=['system'])
def health() -> dict[str, str]:
    return {'status': 'ok'}

@app.post('/auth/login', tags=['auth'])
def login(credentials: HTTPBasicCredentials = Depends(basic), db: Session = Depends(get_db)):
    user = authenticate(db, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    return {'access_token': create_session(db, user), 'token_type': 'bearer', 'expires_in': 28800}

@app.post('/auth/logout', tags=['auth'])
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Authentication required')
    if get_user_by_token(db, credentials.credentials) is None:
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    revoke_session(db, credentials.credentials)
    return {'status': 'ok'}

@app.get('/auth/me', tags=['auth'])
def me(user=Depends(current_user)):
    return {'id': user.id, 'username': user.username, 'display_name': user.display_name}

@app.get('/reports/management-summary', tags=['reports'])
def management_summary(
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_management_summary(db, user, project_id, start_at, end_at)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get('/reports/workflow', tags=['reports'])
def workflow_report(
    project_id: int,
    start_at: datetime,
    end_at: datetime,
    report_status: str | None = None,
    operation_type_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_workflow_report(
            db, user, project_id, start_at, end_at,
            status=report_status, operation_type_id=operation_type_id,
            limit=limit, offset=offset,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
