"""Memory Service (Phase A)

Provides user fact storage and semantic retrieval integrating SemanticIndex.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import uuid

# Optional change tracker (not required for core memory operations)
try:  # pragma: no cover - best effort optional import
    from ..database.change_tracker import ChangeTracker  # type: ignore
except Exception:  # pragma: no cover
    ChangeTracker = None  # type: ignore

try:
    from vector.semantic_index import semantic_index
except Exception:
    semantic_index = None  # type: ignore

class MemoryService:
    def __init__(self, mongo_db=None):
        self.db = mongo_db
    # Collections (may be None if mongo not provided)
    self.facts_coll = self.db["mem_facts"] if self.db else None
    self.episodes_coll = self.db["mem_episodes"] if self.db else None

    async def add_fact(self, user_id: str, text: str, importance: float = 0.5, tags: Optional[List[str]] = None) -> str:
        fact_id = str(uuid.uuid4())
        doc = {
            "_id": fact_id,
            "user_id": user_id,
            "text": text,
            "importance": float(importance),
            "tags": tags or [],
            "created_at": datetime.utcnow(),
            "last_used": None,
            "uses": 0
        }
        if self.facts_coll:
            await self.facts_coll.insert_one(doc)
        if semantic_index:
            try:
                semantic_index.add(text, metadata={
                    "type": "fact", "user_id": user_id, "fact_id": fact_id,
                    "importance": float(importance), "created_at": doc["created_at"].isoformat()
                })
            except Exception:
                pass
        return fact_id

    async def search_facts(self, user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # If semantic index available, use it scoped by user
        if semantic_index:
            try:
                results = semantic_index.search_with_meta(query, top_k=top_k, metadata_filter={"user_id": user_id, "type": "fact"})
                return [
                    {"text": r["text"], "score": r["score"], **({'metadata': r.get('metadata')} if r.get('metadata') else {})}
                    for r in results
                ]
            except Exception:
                pass
        # fallback naive query in Mongo
        if self.facts_coll:
            cursor = self.facts_coll.find({"user_id": user_id, "text": {"$regex": query, "$options": "i"}}).limit(top_k)
            return [{"text": d.get("text"), "score": 0.0, "importance": d.get("importance"), "id": d.get("_id")} async for d in cursor]
        return []

    async def add_episode(self, user_id: str, event_type: str, payload: Dict[str, Any], importance: float = 0.4) -> str:
        eid = str(uuid.uuid4())
        doc = {
            "_id": eid,
            "user_id": user_id,
            "event_type": event_type,
            "payload": payload,
            "ts": datetime.utcnow(),
            "importance": float(importance),
            "last_used": None,
            "uses": 0
        }
        if self.episodes_coll:
            await self.episodes_coll.insert_one(doc)
        # Optionally index textual summary
        if semantic_index:
            try:
                summary = f"{event_type}: {payload}"[:500]
                semantic_index.add(summary, metadata={
                    "type": "episode", "user_id": user_id, "episode_id": eid, "event_type": event_type,
                    "importance": float(importance), "ts": doc["ts"].isoformat()
                })
            except Exception:
                pass
        return eid

    async def search(self, user_id: str, query: str, top_k: int = 8, include: List[str] | None = None) -> Dict[str, Any]:
        include = include or ["facts", "episodes"]
        results = {"facts": [], "episodes": []}
        if "facts" in include:
            results["facts"] = await self.search_facts(user_id, query, top_k=top_k)
        if "episodes" in include and semantic_index:
            try:
                ep = semantic_index.search_with_meta(query, top_k=top_k, metadata_filter={"user_id": user_id, "type": "episode"})
                results["episodes"] = ep
            except Exception:
                pass
        return results

    async def list_episodes(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.episodes_coll:
            return []
        cursor = self.episodes_coll.find({"user_id": user_id}).sort("ts", -1).limit(limit)
        return [
            {"id": d.get("_id"), "event_type": d.get("event_type"), "ts": d.get("ts"), "payload": d.get("payload"), "importance": d.get("importance", 0.4), "uses": d.get("uses", 0)}
            async for d in cursor
        ]

    async def mark_used(self, fact_id: str):
        if not self.facts_coll:
            return
        await self.facts_coll.update_one({"_id": fact_id}, {"$set": {"last_used": datetime.utcnow()}, "$inc": {"uses": 1}})

    async def mark_episode_used(self, episode_id: str):
        if not self.episodes_coll:
            return
        await self.episodes_coll.update_one({"_id": episode_id}, {"$set": {"last_used": datetime.utcnow()}, "$inc": {"uses": 1}})

    async def list_facts(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.facts_coll:
            return []
        cursor = self.facts_coll.find({"user_id": user_id}).sort("importance", -1).limit(limit)
        return [
            {"id": d.get("_id"), "text": d.get("text"), "importance": d.get("importance"), "uses": d.get("uses", 0)}
            async for d in cursor
        ]

    # Phase C: unified retrieval with ranking formula
    def _rank(self, raw_score: float, importance: float, created_at: Optional[datetime], last_used: Optional[datetime], uses: int) -> float:
        # freshness factor based on recency (created_at or last_used)
        now = datetime.utcnow()
        ref_time = last_used or created_at or now
        age_days = max((now - ref_time).total_seconds() / 86400.0, 0.0)
        freshness = 1.0 / (1.0 + age_days / 30.0)  # decays over ~1 month
        usage_factor = 1.0 + min(uses, 50) / 200.0  # up to +0.25
        importance_factor = 0.7 + 0.3 * max(min(importance, 1.0), 0.0)
        return raw_score * importance_factor * freshness * usage_factor

    async def retrieve(self, user_id: str, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        # get semantic matches for facts and episodes separately
        combined: List[Tuple[str, Dict[str, Any]]] = []  # (type, data)
        fact_results = await self.search_facts(user_id, query, top_k=top_k)
        for fr in fact_results:
            meta = fr.get('metadata', {}) if isinstance(fr, dict) else {}
            importance = meta.get('importance') or 0.5
            created_at_iso = meta.get('created_at')
            created_at = None
            if created_at_iso:
                try:
                    created_at = datetime.fromisoformat(created_at_iso.replace('Z','+00:00'))
                except Exception:
                    created_at = None
            rank_score = self._rank(fr.get('score', 0.0), float(importance), created_at, None, 0)
            combined.append(("fact", {"type": "fact", "text": fr.get('text'), "raw_score": fr.get('score'), "rank": rank_score, "metadata": meta}))
        if semantic_index:
            try:
                ep_results = semantic_index.search_with_meta(query, top_k=top_k, metadata_filter={"user_id": user_id, "type": "episode"})
                for er in ep_results:
                    meta = er.get('metadata') or {}
                    importance = meta.get('importance') or 0.4
                    ts_iso = meta.get('ts')
                    ts_dt = None
                    if ts_iso:
                        try:
                            ts_dt = datetime.fromisoformat(ts_iso.replace('Z','+00:00'))
                        except Exception:
                            ts_dt = None
                    rank_score = self._rank(er.get('score', 0.0), float(importance), ts_dt, None, 0)
                    combined.append(("episode", {"type": "episode", "text": er.get('text'), "raw_score": er.get('score'), "rank": rank_score, "metadata": meta}))
            except Exception:
                pass
        # sort by rank
        combined.sort(key=lambda x: x[1]['rank'], reverse=True)
        # slice
        top = [c[1] for c in combined[:top_k]]
        return top

    async def decay_importance(self, user_id: Optional[str] = None, idle_days: int = 30, decay: float = 0.05):
        """Reduce importance slightly for items not used recently.

        Args:
            user_id: if provided restrict to user.
            idle_days: threshold for decay.
            decay: amount to subtract (clamped).
        """
        if not self.facts_coll:
            return 0
        cutoff = datetime.utcnow() - timedelta(days=idle_days)  # type: ignore[name-defined]
        q: Dict[str, Any] = {"$or": [{"last_used": None}, {"last_used": {"$lt": cutoff}}]}
        if user_id:
            q['user_id'] = user_id
        docs = self.facts_coll.find(q).limit(500)
        updated = 0
        async for d in docs:
            imp = float(d.get('importance', 0.5))
            new_imp = max(0.0, imp - decay)
            await self.facts_coll.update_one({"_id": d.get('_id')}, {"$set": {"importance": new_imp}})
            updated += 1
        return updated

    async def purge(self, item_id: str, item_type: str) -> bool:
        if item_type == 'fact' and self.facts_coll:
            res = await self.facts_coll.delete_one({"_id": item_id})
            return res.deleted_count > 0  # type: ignore[attr-defined]
        if item_type == 'episode' and self.episodes_coll:
            res = await self.episodes_coll.delete_one({"_id": item_id})
            return res.deleted_count > 0  # type: ignore[attr-defined]
        return False

memory_service: Optional[MemoryService] = None
