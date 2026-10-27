from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.column_types import UTCDateTime
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    user: Mapped[User] = relationship(back_populates="sessions")


class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    developer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(160), nullable=True)
    release_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    user_games: Mapped[list["UserGame"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class UserGame(Base):
    __tablename__ = "user_games"
    __table_args__ = (UniqueConstraint("user_id", "game_id", "platform", name="uq_user_game_platform"),
                      UniqueConstraint("user_id", "external_game_id", name="uq_user_external_game"),
                      CheckConstraint("rating IS NULL OR (rating >= 0 AND rating <= 10)", name="ck_rating_0_10"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(80), default="PC")
    genre: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="backlog", index=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    tags: Mapped[str] = mapped_column(Text, default="[]")
    personal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_override_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_game_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    imported_playtime_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    game: Mapped[Game] = relationship(back_populates="user_games")


class GamingSession(Base):
    __tablename__ = "gaming_sessions"
    __table_args__ = (CheckConstraint("duration_seconds >= 0", name="ck_session_duration_nonnegative"),
                      Index("ix_session_user_start", "user_id", "started_at"),
                      Index("uq_active_gaming_session_user", "user_id", unique=True,
                            sqlite_where=text("state IN ('running', 'paused')"),
                            postgresql_where=text("state IN ('running', 'paused')")))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_game_id: Mapped[str] = mapped_column(ForeignKey("user_games.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="completed")
    paused_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    paused_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (CheckConstraint("target > 0", name="ck_goal_target_positive"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal_type: Mapped[str] = mapped_column(String(30))
    target: Mapped[float] = mapped_column(Float)
    deadline: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class GoalGame(Base):
    __tablename__ = "goal_games"
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True)
    user_game_id: Mapped[str] = mapped_column(ForeignKey("user_games.id", ondelete="CASCADE"), primary_key=True)


class PlatformConnection(Base):
    __tablename__ = "platform_connections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    external_user_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="disconnected")
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)


class SteamOpenIDNonce(Base):
    __tablename__ = "steam_openid_nonces"
    nonce_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    connection_id: Mapped[str] = mapped_column(ForeignKey("platform_connections.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)


class GameNote(Base):
    __tablename__ = "game_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_game_id: Mapped[str] = mapped_column(ForeignKey("user_games.id", ondelete="CASCADE"), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    theme: Mapped[str] = mapped_column(String(20), default="dark")
    weekly_goal_hours: Mapped[float] = mapped_column(Float, default=10.0)
    timezone: Mapped[str] = mapped_column(String(80), default="America/Sao_Paulo")
    profile_public: Mapped[bool] = mapped_column(Boolean, default=False)
