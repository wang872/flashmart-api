from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import unauthorized
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise unauthorized()
    try:
        username = decode_access_token(creds.credentials)
    except Exception:
        raise unauthorized()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise unauthorized()
    return user


def get_idempotency_key(idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> str:
    return (idempotency_key or "").strip()
