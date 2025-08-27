"""Application middleware: correlation ID, rate limiting, metrics binding."""
from __future__ import annotations
import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable, Awaitable
from .security.ratelimit import RateLimiter
import jwt, os
from .metrics import metrics
from .config.settings import settings


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    ROLE_LIMITS = {
        "admin": (settings.rate_limit_requests * 5, settings.rate_limit_window_seconds),
        "user": (settings.rate_limit_requests, settings.rate_limit_window_seconds),
        "guest": (max(1, int(settings.rate_limit_requests / 2)), settings.rate_limit_window_seconds)
    }

    def __init__(self, app, limiter: RateLimiter, jwt_secret: str | None = None):
        super().__init__(app)
        self.limiter = limiter
        self.jwt_secret = jwt_secret or os.getenv("JWT_SECRET", settings.jwt_secret)

    def _derive_limits(self, roles):
        # pick highest privilege first
        if not roles:
            return self.ROLE_LIMITS["guest"]
        for r in ("admin", "user", "guest"):
            if r in roles:
                return self.ROLE_LIMITS[r]
        return self.ROLE_LIMITS["guest"]

    def _extract_roles(self, request) -> list[str]:
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return []
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
            return payload.get("roles", []) or []
        except Exception:
            return []

    async def dispatch(self, request, call_next):
        roles = self._extract_roles(request)
        limit, window = self._derive_limits(roles)
        key_base = request.client.host if request.client else "anonymous"
        # differentiate per-role to avoid cross-role contention
        key = f"{key_base}:{','.join(sorted(roles)) or 'guest'}"
        allowed, remaining, applied = self.limiter.check(key, limit=limit, window=window)
        if not allowed:
            return JSONResponse({"detail": "Rate limit exceeded", "limit": applied, "window": window}, status_code=429)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(applied)
        response.headers["X-RateLimit-Window"] = str(window)
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not settings.enable_metrics:
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        try:
            metrics.request_counter.labels(method=request.method, path=request.url.path, status=str(response.status_code)).inc()
            metrics.request_latency.labels(method=request.method, path=request.url.path).observe(duration)
        except Exception:
            pass
        return response
