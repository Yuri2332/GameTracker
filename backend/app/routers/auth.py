from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuthSession, User, UserSettings
from app.schemas import LoginIn, RegisterIn, UserOut
from app.security import hash_password, hash_token, new_csrf_token, new_session_token, session_expiry, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])
_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = Lock()


def rate_limit(request: Request, action: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    key = f"{request.client.host if request.client else 'unknown'}:{action}"
    with _attempts_lock:
        _attempts[key] = [stamp for stamp in _attempts[key] if now - stamp < 900]
        if len(_attempts[key]) >= 10:
            raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos.")
        _attempts[key].append(now)


def issue_cookies(response: Response, db: Session, user: User) -> None:
    raw_token = new_session_token()
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(raw_token), expires_at=session_expiry()))
    csrf = new_csrf_token()
    response.set_cookie("gametracker_session", raw_token, max_age=settings.session_ttl_days * 86400,
                        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
    response.set_cookie("gametracker_csrf", csrf, max_age=settings.session_ttl_days * 86400,
                        httponly=False, secure=settings.cookie_secure, samesite="lax", path="/")


@router.get("/csrf")
def get_csrf(response: Response, gametracker_csrf: str | None = Cookie(default=None)):
    # The frontend can also obtain this value by reading the non-HttpOnly cookie.
    token = gametracker_csrf or new_csrf_token()
    response.set_cookie("gametracker_csrf", token, max_age=settings.session_ttl_days * 86400,
                        httponly=False, secure=settings.cookie_secure, samesite="lax", path="/")
    return {"csrf_token": token}


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "register")
    email = payload.email.lower()
    username = payload.username.strip()
    if db.query(User).filter((User.email == email) | (User.username.ilike(username))).first():
        raise HTTPException(status_code=409, detail="E-mail ou nome de usuário já cadastrado")
    user = User(email=email, username=username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        db.add(UserSettings(user_id=user.id))
        issue_cookies(response, db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail ou nome de usuário já cadastrado")
    db.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "login")
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    issue_cookies(response, db, user)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(response: Response, gametracker_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if gametracker_session:
        auth_session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(gametracker_session)).first()
        if auth_session:
            db.delete(auth_session)
            db.commit()
    response.delete_cookie("gametracker_session", path="/")
    response.delete_cookie("gametracker_csrf", path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
