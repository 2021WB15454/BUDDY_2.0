"""Centralized application settings using Pydantic BaseSettings.

Phase 1 settings consolidation. Later phases can extend with:
 - Dynamic reloading
 - Remote config providers (Firebase Remote Config, GCS, etc.)
 - Secrets manager integration (GCP Secret Manager / AWS SM)
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional
import os


class Settings:
    # Core
    app_name: str = "BUDDY AI Assistant"
    environment: str = "development"
    version: str = "2.0.0"
    debug: bool = False

    # Security / Auth
    jwt_secret: str = "change-me-in-prod"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    allowed_origins: List[str] = ["*"]

    # Database
    mongodb_uri: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Observability
    enable_metrics: bool = True
    enable_tracing: bool = False
    trace_sample_ratio: float = 1.0

    # Internationalisation
    default_locale: str = "en"
    supported_locales: List[str] = ["en", "es", "fr"]

    # Token / context management
    max_context_tokens: int = 2000
    max_response_tokens: int = 512

    # Vector / RAG
    vector_backend: str = "inmemory"  # choices: inmemory, faiss, chroma
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 80

    # Redis / persistence backends
    redis_url: Optional[str] = None

    # Security / rotation
    jwt_active_kid: str = "primary"
    encryption_key_version: str = "v1"

    # Streaming / performance
    streaming_flush_interval_ms: int = 50
    max_stream_latency_ms: int = 2000

    # Logging
    enable_log_sampling: bool = False
    log_sample_rate: float = 0.1
    scrub_pii: bool = True


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Populate from environment (simple mapping)
    def getenv(name, default):
        return os.getenv(name, default)
    s.app_name = getenv("BUDDY_APP_NAME", s.app_name)
    s.environment = getenv("BUDDY_ENV", s.environment)
    s.version = getenv("BUDDY_VERSION", s.version)
    s.debug = getenv("BUDDY_DEBUG", str(s.debug)).lower() == "true"
    s.jwt_secret = getenv("BUDDY_JWT_SECRET", s.jwt_secret)
    s.access_token_minutes = int(getenv("BUDDY_ACCESS_TOKEN_MINUTES", str(s.access_token_minutes)))
    s.refresh_token_days = int(getenv("BUDDY_REFRESH_TOKEN_DAYS", str(s.refresh_token_days)))
    s.mongodb_uri = os.getenv("MONGODB_URI", s.mongodb_uri)
    s.openai_api_key = os.getenv("OPENAI_API_KEY", s.openai_api_key)
    s.rate_limit_requests = int(getenv("BUDDY_RATE_LIMIT_REQUESTS", str(s.rate_limit_requests)))
    s.rate_limit_window_seconds = int(getenv("BUDDY_RATE_LIMIT_WINDOW", str(s.rate_limit_window_seconds)))
    s.enable_metrics = getenv("BUDDY_ENABLE_METRICS", str(s.enable_metrics)).lower() == "true"
    s.enable_tracing = getenv("BUDDY_ENABLE_TRACING", str(s.enable_tracing)).lower() == "true"
    s.trace_sample_ratio = float(getenv("BUDDY_TRACE_SAMPLE_RATIO", str(s.trace_sample_ratio)))
    s.default_locale = getenv("BUDDY_DEFAULT_LOCALE", s.default_locale)
    supp = getenv("BUDDY_SUPPORTED_LOCALES", ",".join(s.supported_locales))
    s.supported_locales = [x.strip() for x in supp.split(",") if x.strip()]
    s.max_context_tokens = int(getenv("BUDDY_MAX_CONTEXT_TOKENS", str(s.max_context_tokens)))
    s.max_response_tokens = int(getenv("BUDDY_MAX_RESPONSE_TOKENS", str(s.max_response_tokens)))
    s.vector_backend = getenv("BUDDY_VECTOR_BACKEND", s.vector_backend)
    s.rag_chunk_size = int(getenv("BUDDY_RAG_CHUNK_SIZE", str(s.rag_chunk_size)))
    s.rag_chunk_overlap = int(getenv("BUDDY_RAG_CHUNK_OVERLAP", str(s.rag_chunk_overlap)))
    s.redis_url = os.getenv("REDIS_URL", s.redis_url)
    s.jwt_active_kid = getenv("BUDDY_JWT_ACTIVE_KID", s.jwt_active_kid)
    s.encryption_key_version = getenv("BUDDY_ENC_KEY_VERSION", s.encryption_key_version)
    s.streaming_flush_interval_ms = int(getenv("BUDDY_STREAM_FLUSH_MS", str(s.streaming_flush_interval_ms)))
    s.max_stream_latency_ms = int(getenv("BUDDY_MAX_STREAM_LATENCY_MS", str(s.max_stream_latency_ms)))
    s.enable_log_sampling = getenv("BUDDY_ENABLE_LOG_SAMPLING", str(s.enable_log_sampling)).lower() == "true"
    s.log_sample_rate = float(getenv("BUDDY_LOG_SAMPLE_RATE", str(s.log_sample_rate)))
    s.scrub_pii = getenv("BUDDY_SCRUB_PII", str(s.scrub_pii)).lower() == "true"
    # allowed origins list
    origins_raw = getenv("BUDDY_ALLOWED_ORIGINS", ",".join(s.allowed_origins))
    s.allowed_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
    return s


settings = get_settings()
