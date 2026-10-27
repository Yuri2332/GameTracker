import csv
import io
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import GamingSession, Game, Goal, User, UserGame, UserSettings
from app.schemas import ProfileUpdate, SettingsUpdate, UserOut
from app.services import game_dict, goal_dict, local_datetime, timezone_for_user, utc_aware, week_start

router = APIRouter(tags=["dashboard and statistics"])


def completed_sessions(db: Session, user_id: str):
    return db.query(GamingSession).filter(GamingSession.user_id == user_id, GamingSession.state == "completed").all()


def hours_by_game(db: Session, user: User) -> list[dict]:
    rows = db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.user_id == user.id).all()
    totals = []
    for row in rows:
        seconds = db.query(func.coalesce(func.sum(GamingSession.duration_seconds), 0)).filter(
            GamingSession.user_game_id == row.id, GamingSession.state == "completed").scalar() or 0
        hours = (seconds + row.imported_playtime_minutes * 60) / 3600
        totals.append({"id": row.id, "name": row.game.name, "cover_url": row.cover_override_url or row.game.cover_url,
                       "platform": row.platform, "genre": row.genre or "Sem gênero", "status": row.status,
                       "hours": round(hours, 1), "rating": row.rating})
    return totals


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    user_timezone = timezone_for_user(db, user.id)
    local_now = now.astimezone(user_timezone)
    week = week_start(now, user_timezone)
    month_start = datetime.combine(local_now.date().replace(day=1), time.min, tzinfo=user_timezone).astimezone(timezone.utc)
    all_games = db.query(UserGame).filter(UserGame.user_id == user.id).count()
    session_rows = completed_sessions(db, user.id)
    completed_seconds = sum(row.duration_seconds for row in session_rows)
    imported_minutes = db.query(func.coalesce(func.sum(UserGame.imported_playtime_minutes), 0)).filter(UserGame.user_id == user.id).scalar() or 0
    week_seconds = sum(row.duration_seconds for row in session_rows if utc_aware(row.started_at) >= week)
    month_seconds = sum(row.duration_seconds for row in session_rows if utc_aware(row.started_at) >= month_start)
    by_game = hours_by_game(db, user)
    most_played = max(by_game, key=lambda item: item["hours"], default=None)
    sessions_count = len(session_rows)
    daily = []
    for offset in range(6, -1, -1):
        day = local_now.date() - timedelta(days=offset)
        secs = sum(row.duration_seconds for row in session_rows if local_datetime(row.started_at, user_timezone).date() == day)
        daily.append({"date": day.isoformat(), "hours": round(secs / 3600, 2)})
    recent_session_rows = db.query(GamingSession).filter(GamingSession.user_id == user.id).order_by(GamingSession.started_at.desc()).limit(5).all()
    last_by_user_game: dict[str, datetime] = {}
    for row in db.query(GamingSession).filter(GamingSession.user_id == user.id).order_by(GamingSession.started_at.desc()).all():
        if row.user_game_id not in last_by_user_game: last_by_user_game[row.user_game_id] = row.started_at
    game_rows = db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.user_id == user.id).all()
    recent_games = sorted(game_rows, key=lambda row: last_by_user_game.get(row.id, row.created_at), reverse=True)[:6]
    favorites = [game_dict(db, row) for row in game_rows if row.favorite][:4]
    settings_row = db.get(UserSettings, user.id)
    weekly_goal = settings_row.weekly_goal_hours if settings_row else 10
    goals = db.query(Goal).filter(Goal.user_id == user.id, Goal.status == "active").order_by(Goal.created_at.desc()).limit(4).all()
    return {"totals": {"games": all_games, "hours": round(completed_seconds / 3600 + imported_minutes / 60, 1),
                        "week_hours": round(week_seconds / 3600, 1), "sessions": sessions_count,
                        "most_played": most_played},
            "weekly_goal": {"target": weekly_goal, "progress": round(week_seconds / 3600, 1),
                            "percentage": min(100, round(week_seconds / 3600 / weekly_goal * 100))},
            "activity": daily, "monthly_hours": round(month_seconds / 3600, 1),
            "recent_games": [game_dict(db, row) for row in recent_games], "favorites": favorites,
            "recent_sessions": [{"id": row.id, "game_id": row.user_game_id, "started_at": row.started_at,
                                 "duration_seconds": row.duration_seconds, "note": row.note,
                                 "game_name": db.get(Game, db.get(UserGame, row.user_game_id).game_id).name}
                                for row in recent_session_rows],
            "goals": [goal_dict(db, row) for row in goals]}


@router.get("/statistics")
def statistics(days: int = Query(default=30, ge=7, le=365), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    user_timezone = timezone_for_user(db, user.id)
    local_now = now.astimezone(user_timezone)
    start_date = local_now.date() - timedelta(days=days - 1)
    start = datetime.combine(start_date, time.min, tzinfo=user_timezone).astimezone(timezone.utc)
    rows = db.query(GamingSession).filter(GamingSession.user_id == user.id, GamingSession.state == "completed",
                                         GamingSession.started_at >= start).all()
    activity = []
    for offset in range(days - 1, -1, -1):
        day = local_now.date() - timedelta(days=offset)
        seconds = sum(row.duration_seconds for row in rows if local_datetime(row.started_at, user_timezone).date() == day)
        activity.append({"date": day.isoformat(), "hours": round(seconds / 3600, 2)})
    period_seconds: dict[str, int] = {}
    for session in rows:
        period_seconds[session.user_game_id] = period_seconds.get(session.user_game_id, 0) + session.duration_seconds
    user_games = db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.user_id == user.id).all()
    game_hours = [{"id": row.id, "name": row.game.name, "cover_url": row.cover_override_url or row.game.cover_url,
                   "platform": row.platform, "genre": row.genre or "Sem gênero", "status": row.status,
                   "hours": round(period_seconds.get(row.id, 0) / 3600, 1), "rating": row.rating}
                  for row in user_games]
    by_platform: dict[str, float] = {}
    by_genre: dict[str, float] = {}
    for entry in game_hours:
        if entry["hours"] <= 0: continue
        by_platform[entry["platform"]] = by_platform.get(entry["platform"], 0) + entry["hours"]
        by_genre[entry["genre"]] = by_genre.get(entry["genre"], 0) + entry["hours"]
    status_counts = {key: 0 for key in ["backlog", "playing", "paused", "completed"]}
    for row in db.query(UserGame.status).filter(UserGame.user_id == user.id).all():
        status_counts[row[0]] = status_counts.get(row[0], 0) + 1
    previous_start = datetime.combine(start_date - timedelta(days=days), time.min, tzinfo=user_timezone).astimezone(timezone.utc)
    previous_rows = db.query(GamingSession.duration_seconds).filter(GamingSession.user_id == user.id,
                      GamingSession.state == "completed", GamingSession.started_at >= previous_start,
                      GamingSession.started_at < start).all()
    current_hours = sum(row.duration_seconds for row in rows) / 3600
    previous_hours = sum(row[0] for row in previous_rows) / 3600
    comparison = round(((current_hours - previous_hours) / previous_hours) * 100, 1) if previous_hours else None
    day_hours: dict[str, float] = {}
    hour_counts = {str(hour): 0 for hour in range(24)}
    weekdays = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    for row in rows:
        local_start = local_datetime(row.started_at, user_timezone)
        day_name = weekdays[local_start.weekday()]
        day_hours[day_name] = day_hours.get(day_name, 0) + row.duration_seconds / 3600
        hour_counts[str(local_start.hour)] += 1
    avg = sum(row.duration_seconds for row in rows) / max(1, len(rows)) / 3600
    return {"period_days": days, "activity": activity, "total_hours": round(current_hours, 1),
            "session_count": len(rows), "average_session_hours": round(avg, 2),
            "comparison_percent": comparison,
            "top_games": sorted((entry for entry in game_hours if entry["hours"] > 0), key=lambda x: x["hours"], reverse=True)[:8],
            "platform_hours": [{"name": k, "hours": round(v, 1)} for k, v in sorted(by_platform.items(), key=lambda x: -x[1])],
            "genre_hours": [{"name": k, "hours": round(v, 1)} for k, v in sorted(by_genre.items(), key=lambda x: -x[1])],
            "status_counts": status_counts, "hours_by_weekday": day_hours, "sessions_by_hour": hour_counts}


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UserSettings, user.id)
    if not row:
        row = UserSettings(user_id=user.id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"theme": row.theme, "weekly_goal_hours": row.weekly_goal_hours, "timezone": row.timezone,
            "profile_public": row.profile_public}


@router.patch("/settings")
def update_settings(payload: SettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UserSettings, user.id)
    if not row:
        row = UserSettings(user_id=user.id)
        db.add(row)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    db.commit()
    return {"theme": row.theme, "weekly_goal_hours": row.weekly_goal_hours, "timezone": row.timezone,
            "profile_public": row.profile_public}


@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = dashboard(user, db)
    return {"username": user.username, "email": user.email, "avatar_url": user.avatar_url,
            "created_at": user.created_at, "totals": data["totals"], "favorite_game": data["totals"]["most_played"]}


@router.patch("/profile", response_model=UserOut)
def update_profile(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    if "username" in data:
        data["username"] = data["username"].strip()
        existing = db.query(User.id).filter(User.id != user.id, User.username.ilike(data["username"])).first()
        if existing: raise HTTPException(status_code=409, detail="Este nome de usuário já está em uso")
    if "avatar_url" in data: data["avatar_url"] = str(data["avatar_url"]) if data["avatar_url"] else None
    for key, value in data.items(): setattr(user, key, value)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Este nome de usuário já está em uso")
    db.refresh(user)
    return user


@router.delete("/profile", status_code=204)
def delete_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()


@router.get("/export")
def export_data(format: str = Query(default="json", pattern="^(json|csv)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    games = [game_dict(db, row) for row in db.query(UserGame).options(joinedload(UserGame.game)).filter(UserGame.user_id == user.id).all()]
    sessions = db.query(GamingSession).filter(GamingSession.user_id == user.id).order_by(GamingSession.started_at.asc()).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    settings_row = db.get(UserSettings, user.id)
    session_items = []
    for row in sessions:
        ug = db.get(UserGame, row.user_game_id)
        game = db.get(Game, ug.game_id) if ug else None
        session_items.append({"game": game.name if game else "Jogo removido", "started_at": row.started_at.isoformat(),
                              "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                              "duration_seconds": row.duration_seconds, "source": row.source, "note": row.note})
    if format == "json":
        import json
        goal_items = [goal_dict(db, goal) for goal in goals]
        settings_item = {"theme": settings_row.theme, "weekly_goal_hours": settings_row.weekly_goal_hours,
                         "timezone": settings_row.timezone, "profile_public": settings_row.profile_public} if settings_row else None
        return Response(content=json.dumps({"profile": {"username": user.username, "email": user.email,
                                 "created_at": user.created_at}, "games": games, "sessions": session_items,
                                 "goals": goal_items, "settings": settings_item}, ensure_ascii=False, default=str),
                        media_type="application/json", headers={"Content-Disposition": "attachment; filename=gametracker-export.json"})
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=["game", "started_at", "ended_at", "duration_seconds", "source", "note"])
    writer.writeheader()
    writer.writerows(session_items)
    return Response(content=stream.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=gametracker-sessions.csv"})
