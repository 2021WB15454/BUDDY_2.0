"""Prometheus metrics registry."""
from __future__ import annotations
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response


class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.request_counter = Counter(
            "buddy_requests_total", "Total HTTP requests", ["method", "path", "status"], registry=self.registry
        )
        self.request_latency = Histogram(
            "buddy_request_latency_seconds", "Request latency", ["method", "path"], registry=self.registry
        )

    def router(self) -> APIRouter:
        r = APIRouter()

        @r.get("/metrics")
        async def metrics_endpoint():
            data = generate_latest(self.registry)
            return Response(content=data, media_type=CONTENT_TYPE_LATEST)

        return r


metrics = Metrics()
