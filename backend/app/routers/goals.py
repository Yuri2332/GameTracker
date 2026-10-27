from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Goal, GoalGame, User, UserGame
from app.schemas import GoalCreate, GoalUpdate
from app.services import goal_dict

router = APIRouter(prefix="/goals", tags=["goals"])


def set_games(db: Session, user: User, goal: Goal, game_ids: list[str]):
    if game_ids:
        owned = {row[0] for row in db.query(UserGame.id).filter(UserGame.user_id == user.id, UserGame.id.in_(game_ids)).all()}
        if owned != set(game_ids): raise HTTPException(status_code=422, detail="Uma ou mais escolhas não pertencem à sua biblioteca")
    db.query(GoalGame).filter(GoalGame.goal_id == goal.id).delete()
    for game_id in set(game_ids): db.add(GoalGame(goal_id=goal.id, user_game_id=game_id))


@router.get("")
def list_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).all()
    return {"items": [goal_dict(db, row) for row in rows]}


@router.post("", status_code=201)
def create_goal(payload: GoalCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.goal_type in {"game_hours", "finish_game"} and not payload.game_ids:
        raise HTTPException(status_code=422, detail="Selecione ao menos um jogo para esta meta")
    row = Goal(user_id=user.id, title=payload.title.strip(), description=payload.description,
               goal_type=payload.goal_type, target=payload.target, deadline=payload.deadline, status="active")
    db.add(row)
    db.flush()
    set_games(db, user, row, payload.game_ids)
    db.commit()
    db.refresh(row)
    return goal_dict(db, row)


@router.patch("/{goal_id}")
def update_goal(goal_id: str, payload: GoalUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not row: raise HTTPException(status_code=404, detail="Meta não encontrada")
    data = payload.model_dump(exclude_unset=True)
    game_ids = data.pop("game_ids", None)
    for key, value in data.items(): setattr(row, key, value)
    if game_ids is not None: set_games(db, user, row, game_ids)
    db.commit()
    db.refresh(row)
    return goal_dict(db, row)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not row: raise HTTPException(status_code=404, detail="Meta não encontrada")
    db.delete(row)
    db.commit()
