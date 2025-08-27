"""User profile preference persistence (Mongo-backed if available)."""
from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from mongodb_integration import get_database  # type: ignore
    MONGO_OK = True
except Exception:
    MONGO_OK = False

_memory_profiles: Dict[str, Dict[str, Any]] = {}

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    if MONGO_OK:
        try:
            db = await get_database()
            coll = getattr(db, 'get_collection', lambda name: None)("user_profiles")  # type: ignore
            if coll and hasattr(coll, 'find_one'):
                doc = await coll.find_one({"user_id": user_id})  # type: ignore
                if doc:
                    d = dict(doc)
                    d.pop('_id', None)
                    return d
        except Exception:
            pass
    return _memory_profiles.get(user_id, {"user_id": user_id, "created_at": datetime.utcnow().isoformat()})

async def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    profile = await get_user_profile(user_id)
    profile.update(updates)
    profile["updated_at"] = datetime.utcnow().isoformat()
    if MONGO_OK:
        try:
            db = await get_database()
            coll = getattr(db, 'get_collection', lambda name: None)("user_profiles")  # type: ignore
            if coll and hasattr(coll, 'update_one'):
                await coll.update_one({"user_id": user_id}, {"$set": profile}, upsert=True)  # type: ignore
        except Exception:
            pass
    _memory_profiles[user_id] = profile
    return profile
