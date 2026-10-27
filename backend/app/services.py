import json
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import GamingSession, Goal, GoalGame, Game, UserGame, UserSettings


def utc_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def tags_load(value: str) -> list[str]:
    try:
        return json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


def game_dict(db: Session, user_game: UserGame) -> dict:
    seconds = db.query(func.coalesce(func.sum(GamingSession.duration_seconds), 0)).filter(
        GamingSession.user_game_id == user_game.id, GamingSession.state == "completed"
    ).scalar() or 0
    recent = db.query(GamingSession.started_at).filter(GamingSession.user_game_id == user_game.id).order_by(GamingSession.started_at.desc()).first()
    g = user_game.game
    return {
        "id": user_game.id, "game_id": g.id, "name": g.name, "cover_url": user_game.cover_override_url or g.cover_url,
        "description": g.description, "developer": g.developer, "publisher": g.publisher,
        "release_date": g.release_date, "platform": user_game.platform, "genre": user_game.genre,
        "status": user_game.status, "rating": user_game.rating, "favorite": user_game.favorite,
        "tags": tags_load(user_game.tags), "personal_notes": user_game.personal_notes,
        "total_played_hours": round((seconds + user_game.imported_playtime_minutes * 60) / 3600, 1),
        "last_session_at": recent[0] if recent else None, "created_at": user_game.created_at,
    }


def timezone_for_user(db: Session, user_id: str) -> ZoneInfo:
    settings = db.get(UserSettings, user_id)
    try:
        return ZoneInfo(settings.timezone if settings else "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def local_datetime(value: datetime, timezone_info: ZoneInfo) -> datetime:
    return utc_aware(value).astimezone(timezone_info)


def week_start(now: datetime | None = None, timezone_info: ZoneInfo | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    now = utc_aware(now)
    timezone_info = timezone_info or ZoneInfo("UTC")
    monday = (now.astimezone(timezone_info) - timedelta(days=now.astimezone(timezone_info).weekday())).date()
    return datetime.combine(monday, time.min, tzinfo=timezone_info).astimezone(timezone.utc)


def get_goal_progress(db: Session, goal: Goal) -> float:
    links = db.query(GoalGame.user_game_id).filter(GoalGame.goal_id == goal.id).all()
    user_game_ids = [item[0] for item in links]
    now = datetime.now(timezone.utc)
    user_timezone = timezone_for_user(db, goal.user_id)
    week = week_start(now, user_timezone)
    if goal.goal_type == "weekly_hours":
        value = db.query(func.coalesce(func.sum(GamingSession.duration_seconds), 0)).filter(
            GamingSession.user_id == goal.user_id, GamingSession.started_at >= week,
            GamingSession.state == "completed").scalar() or 0
        return value / 3600
    if goal.goal_type == "active_days":
        rows = db.query(GamingSession.started_at).filter(
            GamingSession.user_id == goal.user_id, GamingSession.started_at >= week,
            GamingSession.state == "completed", GamingSession.duration_seconds > 0).all()
        return float(len({local_datetime(row[0], user_timezone).date() for row in rows}))
    if goal.goal_type == "game_hours":
        if not user_game_ids:
            return 0.0
        seconds = db.query(func.coalesce(func.sum(GamingSession.duration_seconds), 0)).filter(
            GamingSession.user_id == goal.user_id, GamingSession.user_game_id.in_(user_game_ids),
            GamingSession.state == "completed").scalar() or 0
        imported = db.query(func.coalesce(func.sum(UserGame.imported_playtime_minutes), 0)).filter(
            UserGame.id.in_(user_game_ids)).scalar() or 0
        return (seconds + imported * 60) / 3600
    if goal.goal_type == "finish_game":
        if not user_game_ids:
            return 0.0
        completed = db.query(func.count(UserGame.id)).filter(UserGame.id.in_(user_game_ids), UserGame.status == "completed").scalar() or 0
        return float(completed)
    return 0.0


def goal_dict(db: Session, goal: Goal) -> dict:
    progress = get_goal_progress(db, goal)
    percentage = min(100, round(progress / goal.target * 100))
    linked = [x[0] for x in db.query(GoalGame.user_game_id).filter(GoalGame.goal_id == goal.id).all()]
    return {"id": goal.id, "title": goal.title, "description": goal.description, "goal_type": goal.goal_type,
            "target": goal.target, "progress": round(progress, 1), "percentage": percentage,
            "deadline": goal.deadline, "status": "completed" if percentage >= 100 and goal.status == "active" else goal.status,
            "game_ids": linked, "created_at": goal.created_at}
