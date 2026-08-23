# backend/src/naka/shared/infrastructure/settings.py
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://naka:naka@localhost:5432/naka"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    environment: str = "development"
    default_locale: str = "mr"
    response_link_base_url: str = "https://naka.in/r"
