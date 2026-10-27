import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Game, GamingSession, User, UserGame
from app.schemas import GameCreate, GameUpdate
from app.services import game_dict

router = APIRouter(prefix="/games", tags=["games"])


def get_user_game(db: Session, user: User, game_id: str) -> UserGame:
    row = db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.id == game_id, UserGame.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Jogo não encontrado na sua biblioteca")
    return row


@router.get("")
def list_games(search: str | None = None, platform: str | None = None, genre: str | None = None,
               status_filter: str | None = Query(default=None, alias="status"), favorite: bool | None = None,
               sort: str = "recent", page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.user_id == user.id)
    if search:
        q = q.join(Game).filter(Game.name.ilike(f"%{search.strip()}%"))
    else:
        q = q.join(Game)
    if platform: q = q.filter(UserGame.platform == platform)
    if genre: q = q.filter(UserGame.genre == genre)
    if status_filter: q = q.filter(UserGame.status == status_filter)
    if favorite is not None: q = q.filter(UserGame.favorite == favorite)
    total = q.count()
    if sort == "name": q = q.order_by(func.lower(Game.name))
    elif sort == "rating": q = q.order_by(UserGame.rating.desc().nullslast(), func.lower(Game.name))
    elif sort == "recent":
        last_played = db.query(GamingSession.user_game_id.label("user_game_id"), func.max(GamingSession.started_at).label("last_played")).group_by(GamingSession.user_game_id).subquery()
        q = q.outerjoin(last_played, last_played.c.user_game_id == UserGame.id).order_by(func.coalesce(last_played.c.last_played, UserGame.created_at).desc())
    if sort == "hours":
        rows = q.all()
        all_items = [game_dict(db, row) for row in rows]
        all_items.sort(key=lambda item: item["total_played_hours"], reverse=True)
        items = all_items[(page - 1) * limit:page * limit]
    else:
        rows = q.offset((page - 1) * limit).limit(limit).all()
        items = [game_dict(db, row) for row in rows]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("", status_code=201)
def create_game(payload: GameCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game = db.query(Game).filter(func.lower(Game.name) == payload.name.lower()).first()
    if game is None:
        game = Game(name=payload.name, description=payload.description,
                    developer=payload.developer, publisher=payload.publisher, release_date=payload.release_date)
        db.add(game)
        db.flush()
    existing = db.query(UserGame).filter(UserGame.user_id == user.id, UserGame.game_id == game.id,
                                         UserGame.platform == payload.platform).first()
    if existing:
        raise HTTPException(status_code=409, detail="Este jogo já está na biblioteca para essa plataforma")
    row = UserGame(user_id=user.id, game_id=game.id, platform=payload.platform, genre=payload.genre,
                   status=payload.status, rating=payload.rating, favorite=payload.favorite,
                   tags=json.dumps(payload.tags, ensure_ascii=False), personal_notes=payload.personal_notes,
                   cover_override_url=payload.cover_url)
    db.add(row)
    db.commit()
    db.refresh(row)
    return game_dict(db, row)


@router.get("/{game_id}")
def get_game(game_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return game_dict(db, get_user_game(db, user, game_id))


@router.patch("/{game_id}")
def update_game(game_id: str, payload: GameUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user_game(db, user, game_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "tags": row.tags = json.dumps(value or [], ensure_ascii=False)
        elif key == "cover_url":
            row.cover_override_url = value
        elif key in {"name", "description", "developer", "publisher", "release_date"}:
            setattr(row.game, key, value)
        else: setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return game_dict(db, row)


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user_game(db, user, game_id)
    db.delete(row)
    db.commit()
