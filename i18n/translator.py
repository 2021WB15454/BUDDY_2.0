"""Minimal i18n translator stub (Phase 1)."""
from __future__ import annotations
from typing import Dict
from . import translations
from infrastructure.config.settings import settings


def translate(key: str, locale: str | None = None) -> str:
    loc = (locale or settings.default_locale).lower()
    table: Dict[str, str] = translations.get(loc, translations.get(settings.default_locale, {}))
    return table.get(key, key)
