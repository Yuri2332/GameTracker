from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GameTracker"
    environment: str = "development"
    database_url: str = "sqlite:///./gametracker.db"
    secret_key: str = "development-only-change-me"
    session_ttl_days: int = 30
    cookie_secure: bool = False
    frontend_origin: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    steam_api_key: str = ""
    steam_redirect_url: str = "http://localhost:8000/api/integrations/steam/callback"

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
