from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import GamingSession, Game, User, UserGame
from app.schemas import SessionCreate, SessionUpdate
from app.services import utc_aware

router = APIRouter(prefix="/sessions", tags=["sessions"])


def owned_game(db: Session, user: User, game_id: str) -> UserGame:
    row = db.query(UserGame).filter(UserGame.id == game_id, UserGame.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Jogo não encontrado na sua biblioteca")
    return row


def session_dict(db: Session, row: GamingSession) -> dict:
    user_game = db.query(UserGame).filter(UserGame.id == row.user_game_id).first()
    game = db.get(Game, user_game.game_id) if user_game else None
    duration = row.duration_seconds
    if row.state == "running": duration = max(0, int((datetime.now(timezone.utc) - utc_aware(row.started_at)).total_seconds()) - row.paused_seconds)
    if row.state == "paused" and row.paused_at: duration = max(0, int((utc_aware(row.paused_at) - utc_aware(row.started_at)).total_seconds()) - row.paused_seconds)
    return {"id": row.id, "game_id": row.user_game_id, "game_name": game.name if game else "Jogo removido",
            "cover_url": game.cover_url if game else None, "platform": user_game.platform if user_game else None,
            "started_at": row.started_at, "ended_at": row.ended_at, "duration_seconds": duration,
            "duration_hours": round(duration / 3600, 2), "source": row.source, "note": row.note,
            "state": row.state, "paused_seconds": row.paused_seconds}


def set_duration(row: GamingSession, ended_at: datetime) -> None:
    elapsed = int((utc_aware(ended_at) - utc_aware(row.started_at)).total_seconds()) - row.paused_seconds
    if elapsed <= 0:
        raise HTTPException(status_code=422, detail="A sessão precisa ter duração maior que zero")
    if elapsed > 48 * 3600:
        raise HTTPException(status_code=422, detail="A sessão não pode exceder 48 horas")
    row.duration_seconds = elapsed


def active_session(db: Session, user: User) -> GamingSession | None:
    return db.query(GamingSession).filter(GamingSession.user_id == user.id, GamingSession.state.in_(["running", "paused"])).first()


@router.get("")
def list_sessions(game_id: str | None = None, page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(GamingSession).filter(GamingSession.user_id == user.id)
    if game_id: q = q.filter(GamingSession.user_game_id == game_id)
    total = q.count()
    rows = q.order_by(GamingSession.started_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": [session_dict(db, row) for row in rows], "total": total, "page": page, "limit": limit}


@router.post("", status_code=201)
def create_session(payload: SessionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_game(db, user, payload.game_id)
    start, end = utc_aware(payload.started_at), utc_aware(payload.ended_at)
    if end <= start: raise HTTPException(status_code=422, detail="O término deve ser posterior ao início")
    if end > datetime.now(timezone.utc) + timedelta(minutes=1): raise HTTPException(status_code=422, detail="Sessões manuais precisam estar no passado")
    if (end - start).total_seconds() > 48 * 3600: raise HTTPException(status_code=422, detail="A sessão não pode exceder 48 horas")
    if active_session(db, user): raise HTTPException(status_code=409, detail="Encerre a sessão atual antes de registrar outra")
    overlap = db.query(GamingSession.id).filter(GamingSession.user_id == user.id, GamingSession.state == "completed",
               GamingSession.started_at < end, GamingSession.ended_at > start).first()
    if overlap: raise HTTPException(status_code=409, detail="Este horário se sobrepõe a outra sessão registrada")
    duplicate = db.query(GamingSession).filter(GamingSession.user_id == user.id, GamingSession.user_game_id == payload.game_id,
                                               GamingSession.started_at == start, GamingSession.ended_at == end).first()
    if duplicate: raise HTTPException(status_code=409, detail="Esta sessão já foi registrada")
    row = GamingSession(user_id=user.id, user_game_id=payload.game_id, started_at=start, ended_at=end,
                        duration_seconds=int((end - start).total_seconds()), source="manual", state="completed", note=payload.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    return session_dict(db, row)


@router.patch("/{session_id}")
def update_session(session_id: str, payload: SessionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(GamingSession).filter(GamingSession.id == session_id, GamingSession.user_id == user.id).first()
    if not row: raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if row.state != "completed": raise HTTPException(status_code=409, detail="Encerre o contador antes de editar esta sessão")
    data = payload.model_dump(exclude_unset=True)
    game_id = data.pop("game_id", None)
    if game_id:
        owned_game(db, user, game_id)
        row.user_game_id = game_id
    if "started_at" in data: row.started_at = utc_aware(data.pop("started_at"))
    if "ended_at" in data: row.ended_at = utc_aware(data.pop("ended_at"))
    if "note" in data: row.note = data["note"]
    if not row.ended_at: raise HTTPException(status_code=422, detail="A sessão precisa de horário de término")
    if row.ended_at > datetime.now(timezone.utc) + timedelta(minutes=1): raise HTTPException(status_code=422, detail="Sessões manuais precisam estar no passado")
    overlap = db.query(GamingSession.id).filter(GamingSession.user_id == user.id, GamingSession.id != row.id,
               GamingSession.state == "completed", GamingSession.started_at < utc_aware(row.ended_at),
               GamingSession.ended_at > utc_aware(row.started_at)).first()
    if overlap: raise HTTPException(status_code=409, detail="Este horário se sobrepõe a outra sessão registrada")
    set_duration(row, row.ended_at)
    db.commit()
    db.refresh(row)
    return session_dict(db, row)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(GamingSession).filter(GamingSession.id == session_id, GamingSession.user_id == user.id).first()
    if not row: raise HTTPException(status_code=404, detail="Sessão não encontrada")
    db.delete(row)
    db.commit()


@router.post("/active/start", status_code=201)
def start_timer(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game_id = payload.get("game_id")
    if not isinstance(game_id, str): raise HTTPException(status_code=422, detail="Selecione um jogo")
    game = owned_game(db, user, game_id)
    if active_session(db, user): raise HTTPException(status_code=409, detail="Encerre ou pause a sessão atual antes de iniciar outra")
    now = datetime.now(timezone.utc)
    row = GamingSession(user_id=user.id, user_game_id=game.id, started_at=now, source="manual", state="running")
    db.add(row)
    if game.status == "backlog": game.status = "playing"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma sessão em andamento")
    db.refresh(row)
    return session_dict(db, row)


@router.post("/active/pause")
def pause_timer(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = active_session(db, user)
    if not row or row.state != "running": raise HTTPException(status_code=409, detail="Não há sessão em andamento")
    now = datetime.now(timezone.utc)
    row.paused_at, row.state = now, "paused"
    db.commit()
    return session_dict(db, row)


@router.post("/active/resume")
def resume_timer(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = active_session(db, user)
    if not row or row.state != "paused" or not row.paused_at: raise HTTPException(status_code=409, detail="Não há sessão pausada")
    row.paused_seconds += max(0, int((datetime.now(timezone.utc) - utc_aware(row.paused_at)).total_seconds()))
    row.paused_at, row.state = None, "running"
    db.commit()
    return session_dict(db, row)


@router.post("/active/stop")
def stop_timer(payload: dict | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = active_session(db, user)
    if not row: raise HTTPException(status_code=409, detail="Não há sessão em andamento")
    now = datetime.now(timezone.utc)
    if row.state == "paused" and row.paused_at:
        row.paused_seconds += max(0, int((now - utc_aware(row.paused_at)).total_seconds()))
    row.ended_at, row.state = now, "completed"
    row.paused_at = None
    if payload and isinstance(payload.get("note"), str): row.note = payload["note"][:2000]
    set_duration(row, now)
    db.commit()
    return session_dict(db, row)
