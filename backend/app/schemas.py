from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=10, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    username: str
    avatar_url: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    cover_url: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=5000)
    developer: str | None = Field(default=None, max_length=160)
    publisher: str | None = Field(default=None, max_length=160)
    release_date: date | None = None
    platform: str = Field(default="PC", min_length=1, max_length=80)
    genre: str | None = Field(default=None, max_length=80)
    status: Literal["backlog", "playing", "paused", "completed"] = "backlog"
    rating: float | None = Field(default=None, ge=0, le=10)
    favorite: bool = False
    tags: list[str] = Field(default_factory=list, max_length=30)
    personal_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name", "platform")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Campo não pode ficar vazio")
        return value


class GameUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    cover_url: str | None = Field(default=None, max_length=1000)
    description: str | None = Field(default=None, max_length=5000)
    developer: str | None = Field(default=None, max_length=160)
    publisher: str | None = Field(default=None, max_length=160)
    release_date: date | None = None
    platform: str | None = Field(default=None, min_length=1, max_length=80)
    genre: str | None = Field(default=None, max_length=80)
    status: Literal["backlog", "playing", "paused", "completed"] | None = None
    rating: float | None = Field(default=None, ge=0, le=10)
    favorite: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    personal_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name", "platform")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip()
        if not value: raise ValueError("Campo não pode ficar vazio")
        return value


class SessionCreate(BaseModel):
    game_id: str
    started_at: datetime
    ended_at: datetime
    note: str | None = Field(default=None, max_length=2000)


class SessionUpdate(BaseModel):
    game_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    goal_type: Literal["weekly_hours", "game_hours", "active_days", "finish_game"]
    target: float = Field(gt=0, le=10000)
    deadline: date | None = None
    game_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("Informe um título para a meta")
        return value


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    goal_type: Literal["weekly_hours", "game_hours", "active_days", "finish_game"] | None = None
    target: float | None = Field(default=None, gt=0, le=10000)
    deadline: date | None = None
    status: Literal["active", "paused", "completed"] | None = None
    game_ids: list[str] | None = Field(default=None, max_length=50)

    @field_validator("title")
    @classmethod
    def clean_optional_title(cls, value: str | None) -> str | None:
        if value is None: return value
        value = value.strip()
        if not value: raise ValueError("Informe um título para a meta")
        return value


class SettingsUpdate(BaseModel):
    theme: Literal["dark", "light"] | None = None
    weekly_goal_hours: float | None = Field(default=None, ge=1, le=168)
    timezone: str | None = Field(default=None, max_length=80)
    profile_public: bool | None = None

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None: return value
        try: ZoneInfo(value)
        except ZoneInfoNotFoundError as exc: raise ValueError("Fuso horário desconhecido") from exc
        return value


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    avatar_url: HttpUrl | None = None

