from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_creates_relational_schema(tmp_path):
    database = tmp_path / "migration.db"
    config = Config("backend/alembic.ini")
    config.attributes["database_url"] = f"sqlite:///{database.as_posix()}"
    command.upgrade(config, "head")
    inspector = inspect(create_engine(config.attributes["database_url"]))
    tables = set(inspector.get_table_names())
    assert {"users", "games", "user_games", "gaming_sessions", "goals", "goal_games", "platform_connections", "steam_openid_nonces", "sync_logs", "game_notes", "user_settings"} <= tables
