from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.auth.dependencies import current_user, get_db
from app.auth.service import authenticate, create_session, get_user_by_token, revoke_session

app = FastAPI(title='SABT', version='0.1.0')
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