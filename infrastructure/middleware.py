"""Application middleware: correlation ID, rate limiting, metrics binding."""
from __future__ import annotations
import time, uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable, Awaitable
from .security.ratelimit import RateLimiter
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
    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request, call_next):
        key = request.client.host if request.client else "anonymous"
        allowed, remaining = self.limiter.check(key)
        if not allowed:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
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
