"""Structured logging setup using structlog.

Provides JSON logs in production and pretty console logs in development.
Adds correlation / request IDs (middleware supplies them).
"""
from __future__ import annotations
import logging, sys, os, time
import structlog


def configure_logging(environment: str = "development") -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors = [
        timestamper,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if environment == "production":
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def get_logger(name: str):
    return structlog.get_logger(name)
