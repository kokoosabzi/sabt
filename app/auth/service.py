from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.passwords import hash_password, verify_password
from app.db.models import Session as AuthSession, User

SESSION_TTL = timedelta(hours=8)

def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.active or not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user

def create_session(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.add(AuthSession(user_id=user.id, token_hash=hashlib.sha256(raw.encode()).hexdigest(), created_at=now, expires_at=now + SESSION_TTL))
    db.commit()
    return raw

def get_user_by_token(db: Session, token: str) -> User | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(timezone.utc):
        return None
    return db.get(User, row.user_id)

def revoke_session(db: Session, token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()