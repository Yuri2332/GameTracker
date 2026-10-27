from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.config import settings
from app.models import Game, GamingSession, Goal, GoalGame, User, UserGame, UserSettings
from app.security import hash_password

DEMO_EMAIL = "demo@gametracker.local"
DEMO_PASSWORD = "GameTracker-demo-2026"


def seed() -> None:
    if settings.environment == "production":
        raise RuntimeError("A conta demonstrativa não pode ser criada em produção")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if user:
            return
        user = User(email=DEMO_EMAIL, username="demo", password_hash=hash_password(DEMO_PASSWORD))
        db.add(user)
        db.flush()
        prefs = UserSettings(user_id=user.id, weekly_goal_hours=8, timezone="America/Sao_Paulo")
        db.add(prefs)
        records = [
            ("Hades II", "PC", "Roguelike", "playing", 9.0, True),
            ("Sea of Stars", "Nintendo Switch", "RPG", "completed", 8.5, False),
            ("A Short Hike", "PC", "Aventura", "completed", 9.5, True),
            ("Balatro", "PC", "Estratégia", "paused", 8.0, False),
            ("Hollow Knight: Silksong", "PC", "Metroidvania", "backlog", None, False),
        ]
        user_games: list[UserGame] = []
        for name, platform, genre, status, rating, favorite in records:
            game = Game(name=name)
            db.add(game)
            db.flush()
            user_game = UserGame(user_id=user.id, game_id=game.id, platform=platform, genre=genre,
                                 status=status, rating=rating, favorite=favorite, tags="[]")
            db.add(user_game)
            db.flush()
            user_games.append(user_game)
        now = datetime.now(timezone.utc)
        schedule = [(0, 1, 78), (1, 2, 45), (0, 3, 103), (3, 1, 36), (2, 2, 62), (0, 4, 88),
                    (1, 1, 52), (3, 3, 71), (0, 2, 49), (2, 1, 94), (1, 3, 31), (0, 5, 112),
                    (3, 2, 58), (0, 4, 84), (2, 3, 47), (1, 2, 106), (0, 1, 54), (3, 4, 67)]
        for index, (game_index, days_ago, minutes) in enumerate(schedule):
            end = now - timedelta(days=days_ago, hours=2 + index % 3)
            start = end - timedelta(minutes=minutes)
            db.add(GamingSession(user_id=user.id, user_game_id=user_games[game_index].id,
                                 started_at=start, ended_at=end, duration_seconds=minutes * 60,
                                 source="manual", state="completed", note="Sessão demonstrativa"))
        weekly = Goal(user_id=user.id, title="Explorar 8 horas nesta semana", description="Meta de exemplo com progresso calculado pelas sessões.", goal_type="weekly_hours", target=8, status="active")
        game_goal = Goal(user_id=user.id, title="Mais 6 horas de Hades II", description="Uma meta associada a um jogo específico.", goal_type="game_hours", target=12, status="active")
        db.add_all([weekly, game_goal])
        db.flush()
        db.add(GoalGame(goal_id=game_goal.id, user_game_id=user_games[0].id))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print(f"Conta demonstrativa pronta: {DEMO_EMAIL}")
