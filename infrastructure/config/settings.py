"""Centralized application settings using Pydantic BaseSettings.

Phase 1 settings consolidation. Later phases can extend with:
 - Dynamic reloading
 - Remote config providers (Firebase Remote Config, GCS, etc.)
 - Secrets manager integration (GCP Secret Manager / AWS SM)
"""
from __future__ import annotations

from functools import lru_cache
from pydantic import BaseSettings, Field, AnyHttpUrl
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Core
    app_name: str = Field("BUDDY AI Assistant", env="BUDDY_APP_NAME")
    environment: str = Field("development", env="BUDDY_ENV")
    version: str = Field("2.0.0", env="BUDDY_VERSION")
    debug: bool = Field(False, env="BUDDY_DEBUG")

    # Security / Auth
    jwt_secret: str = Field("change-me-in-prod", env="BUDDY_JWT_SECRET")
    access_token_minutes: int = Field(30, env="BUDDY_ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(7, env="BUDDY_REFRESH_TOKEN_DAYS")
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], env="BUDDY_ALLOWED_ORIGINS")

    # Database
    mongodb_uri: Optional[str] = Field(default=None, env="MONGODB_URI")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # Rate limiting
    rate_limit_requests: int = Field(100, env="BUDDY_RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(60, env="BUDDY_RATE_LIMIT_WINDOW")

    # Observability
    enable_metrics: bool = Field(True, env="BUDDY_ENABLE_METRICS")
    enable_tracing: bool = Field(False, env="BUDDY_ENABLE_TRACING")

    # Internationalisation
    default_locale: str = Field("en", env="BUDDY_DEFAULT_LOCALE")
    supported_locales: List[str] = Field(default_factory=lambda: ["en", "es", "fr"], env="BUDDY_SUPPORTED_LOCALES")

    class Config:
        case_sensitive = False
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
