from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuthSession, User
from app.security import hash_token


def get_current_user(request: Request, gametracker_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not gametracker_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar")
    auth_session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(gametracker_session)).first()
    if not auth_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida")
    expires = auth_session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        db.delete(auth_session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sua sessão expirou")
    user = db.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta não encontrada")
    return user


def require_csrf(request: Request, csrf_token: str | None = Cookie(default=None), csrf_header: str | None = None) -> None:
    # Used by the custom middleware in main.py, where headers are available directly.
    return None
