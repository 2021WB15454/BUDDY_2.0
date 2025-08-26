"""
Minimal Semantic Memory Engine (No Pinecone Dependencies)
For emergency deployment when vector databases aren't available
"""

import logging
from typing import Dict, Any, List, Optional, Union
import math
import pathlib
from datetime import datetime, timezone, timedelta

# Optional richer NLP / vector backends
try:  # spaCy model
    import spacy  # type: ignore
    _SPACY_AVAILABLE = True
    try:
        _NLP = spacy.load("en_core_web_sm")  # Ensure model loaded
    except Exception:
        _NLP = None
except Exception:
    _SPACY_AVAILABLE = False
    _NLP = None

try:  # chroma db for persistent lightweight vector store
    import chromadb  # type: ignore
    try:
        from chromadb.config import Settings  # type: ignore
    except Exception:  # older versions
        Settings = None  # type: ignore
    _CHROMA_AVAILABLE = True
except Exception:
    _CHROMA_AVAILABLE = False

from datetime import datetime

logger = logging.getLogger(__name__)

class MinimalSemanticMemoryEngine:
    """Fallback semantic memory engine that works without vector databases.

    Provides a subset of the interface expected by the advanced semantic memory so the
    rest of the system can operate without raising attribute errors.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.initialized = True
        # Cache structure:
        # { user_id: [ { 'content': str, 'intent': str, 'session_id': str, 'metadata': {...}, 'timestamp': iso, 'role': 'user'|'assistant'} ] }
        self.conversation_cache: Dict[str, List[Dict[str, Any]]] = {}
        # Embedding/index related
        self.enable_embeddings = self.config.get("enable_embeddings", True)
        self.use_chroma = False
        self.chroma_client = None
        self.chroma_collections: Dict[str, Any] = {}
        self.embedding_dim = None
        if self.enable_embeddings:
            self._maybe_initialize_vector_backends()

    def _maybe_initialize_vector_backends(self):
        """Attempt to set up chroma or spaCy based embedding pipeline."""
        if _CHROMA_AVAILABLE:
            try:
                persist_dir = self.config.get("chroma_persist_dir")
                if persist_dir:
                    path = pathlib.Path(persist_dir)
                    path.mkdir(parents=True, exist_ok=True)
                if persist_dir and Settings:
                    self.chroma_client = chromadb.Client(Settings(persist_directory=str(persist_dir), anonymized_telemetry=False))
                    logger.info(f"🧪 MinimalSemanticMemory: Chroma persistent store at {persist_dir}")
                else:
                    self.chroma_client = chromadb.Client()  # in-memory fallback
                    if persist_dir and not Settings:
                        logger.warning("Chroma Settings API unavailable; persistence not enabled")
                self.use_chroma = True
                logger.info("🧪 MinimalSemanticMemory: Chroma backend enabled for similarity search")
            except Exception as e:
                logger.warning(f"Chroma init failed, falling back to local embeddings: {e}")
                self.use_chroma = False
        else:
            logger.debug("Chroma not available; using local lightweight embeddings")
        if _SPACY_AVAILABLE and _NLP is not None:
            if _NLP.meta.get("vectors", {}).get("width"):
                self.embedding_dim = _NLP.meta["vectors"]["width"]
        else:
            logger.debug("spaCy model not available; will use bag-of-words hashing for embeddings")

    def update_config(self, new_config: Dict[str, Any]):
        """Update engine configuration at runtime.

        If persistence dir or embedding flag changes, reinitialize vector backends.
        """
        persist_changed = new_config.get("chroma_persist_dir") != self.config.get("chroma_persist_dir")
        embeddings_flag_changed = new_config.get("enable_embeddings", self.enable_embeddings) != self.enable_embeddings
        max_age_changed = new_config.get("max_age_seconds") != self.config.get("max_age_seconds")
        self.config.update(new_config)
        self.enable_embeddings = self.config.get("enable_embeddings", True)
        # Reinitialize chroma if persistence path changed or embeddings newly enabled
        if persist_changed or embeddings_flag_changed:
            self.chroma_client = None
            self.use_chroma = False
            self.chroma_collections.clear()
            if self.enable_embeddings:
                self._maybe_initialize_vector_backends()
        if max_age_changed:
            logger.info(f"Semantic memory max_age_seconds updated to {self.config.get('max_age_seconds')}")

    def _get_chroma_collection(self, user_id: str):
        if user_id in self.chroma_collections:
            return self.chroma_collections[user_id]
        if not self.chroma_client:
            return None
        collection = self.chroma_client.get_or_create_collection(name=f"buddy_mem_{user_id}")
        self.chroma_collections[user_id] = collection
        return collection

    def _embed_text(self, text: str) -> List[float]:
        """Produce a lightweight embedding.
        Priority: spaCy vector -> hashed bag-of-words fallback.
        """
        if _SPACY_AVAILABLE and _NLP is not None:
            doc = _NLP(text)
            if doc.vector is not None and doc.vector.any():  # type: ignore
                return doc.vector.tolist()  # type: ignore
        # Fallback: simple hashed term frequency vector in fixed dimension
        dims = 256
        vec = [0.0] * dims
        for token in text.lower().split():
            h = hash(token) % dims
            vec[h] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _similarity(self, a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b)) / ((math.sqrt(sum(x * x for x in a)) or 1.0) * (math.sqrt(sum(y * y for y in b)) or 1.0))

    async def initialize(self, conversation_db=None):
        """Initialize without vector databases."""
        logger.info("✅ Minimal Semantic Memory Engine initialized (no vector DB)")
        return True

    async def store_conversation_context(self, *args, **kwargs):
        """Store conversation/message context.

        Supports two call signatures:
        1. Advanced engine style: store_conversation_context(data_dict)
        2. Legacy minimal style: store_conversation_context(user_id, conversation_id, messages, metadata=None)
        """
        # Signature 1: single dict argument
        if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
            data: Dict[str, Any] = args[0]
            user_id: str = str(data.get('user_id') or 'unknown')
            self.conversation_cache.setdefault(user_id, []).append(data)
            # Keep only last N messages per user to bound memory
            max_items = self.config.get('max_items_per_user', 500)
            if len(self.conversation_cache[user_id]) > max_items:
                self.conversation_cache[user_id] = self.conversation_cache[user_id][-max_items:]
            # Vector index insertion
            if self.enable_embeddings and data.get('content'):
                self._index_record(user_id, data)
            self._prune_old(user_id)
            return True

        # Signature 2: user_id, conversation_id, messages[, metadata]
        if len(args) >= 3:
            user_id = str(args[0])
            conversation_id = str(args[1])
            messages: Union[List[Dict[str, Any]], List[Any]] = args[2]
            metadata = args[3] if len(args) > 3 else kwargs.get('metadata') or {}
            # Normalize into individual message records
            for msg in messages:
                record = {
                    'user_id': user_id,
                    'session_id': conversation_id,
                    'content': msg.get('content') if isinstance(msg, dict) else str(msg),
                    'intent': msg.get('intent') if isinstance(msg, dict) else None,
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat(),
                    'role': msg.get('role', 'user') if isinstance(msg, dict) else 'user'
                }
                self.conversation_cache.setdefault(user_id, []).append(record)
                if self.enable_embeddings and record.get('content'):
                    self._index_record(user_id, record)
            max_items = self.config.get('max_items_per_user', 500)
            if len(self.conversation_cache[user_id]) > max_items:
                self.conversation_cache[user_id] = self.conversation_cache[user_id][-max_items:]
            self._prune_old(user_id)
            return True

        logger.warning("MinimalSemanticMemoryEngine.store_conversation_context called with unsupported arguments: %s %s", args, kwargs)
        return False

    async def recall_relevant_context(self, query: str, user_id: str, session_id: Optional[str] = None, limit: int = 5, **kwargs):
        """Recall context relevant to the query using naive keyword matching.

        Returns a list of dicts with keys 'text', 'metadata', 'score' to mirror the advanced engine.
        """
        # If chroma available, leverage vector similarity search
        if self.enable_embeddings and self.use_chroma:
            try:
                col = self._get_chroma_collection(user_id)
                if col:
                    query_emb = self._embed_text(query)
                    q_res = col.query(query_embeddings=[query_emb], n_results=limit)
                    out: List[Dict[str, Any]] = []
                    docs_list = q_res.get('documents') or []
                    metas_list = q_res.get('metadatas') or []
                    dist_list = q_res.get('distances') or []
                    if docs_list and isinstance(docs_list, list):
                        docs = docs_list[0]
                        metas = metas_list[0] if metas_list else []
                        dists = dist_list[0] if dist_list else []
                        for i, doc in enumerate(docs):
                            dist_val = dists[i] if (i < len(dists)) else 0.5
                            score_val = 1.0 - dist_val if isinstance(dist_val, (int, float)) else 0.5
                            out.append({
                                'text': doc,
                                'metadata': metas[i] if i < len(metas) else {},
                                'score': float(f"{score_val:.4f}")
                            })
                    if out:
                        return out
            except Exception as e:
                logger.debug(f"Chroma similarity failed, falling back: {e}")

        # Local embedding similarity fallback
        if self.enable_embeddings:  # hashed / spaCy fallback
            query_vec = self._embed_text(query)
            scored: List[tuple[float, Dict[str, Any]]] = []
            history = list(reversed(self.conversation_cache.get(user_id, [])))
            for record in history:
                if not isinstance(record, dict):
                    continue
                content = record.get('content') or ''
                if not content:
                    continue
                rec_vec = self._embed_text(content)
                sim = self._similarity(query_vec, rec_vec)
                scored.append((sim, record))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            results: List[Dict[str, Any]] = []
            for sim, record in scored[:limit]:
                if not isinstance(record, dict):
                    continue
                results.append({
                    'text': record.get('content', ''),
                    'metadata': {
                        **(record.get('metadata') or {}),
                        'session_id': record.get('session_id'),
                        'role': record.get('role'),
                        'intent': record.get('intent')
                    },
                    'score': float(f"{sim:.4f}")
                })
            if results:
                return results

        # Basic keyword fallback
        results_basic: List[Dict[str, Any]] = []
        query_terms = [t for t in query.lower().split() if t]
        for record in reversed(self.conversation_cache.get(user_id, [])):
            if not isinstance(record, dict):
                continue
            content = (record.get('content') or '').lower()
            if not content:
                continue
            match_count = sum(1 for term in query_terms if term in content)
            if match_count:
                score = match_count / max(len(query_terms), 1)
                results_basic.append({
                    'text': record.get('content', ''),
                    'metadata': {
                        **(record.get('metadata') or {}),
                        'session_id': record.get('session_id'),
                        'role': record.get('role'),
                        'intent': record.get('intent')
                    },
                    'score': float(f"{score:.4f}")
                })
            if len(results_basic) >= limit:
                break
        return results_basic

    # Backwards-compatible alias
    async def retrieve_relevant_context(self, user_id: str, query: str, conversation_id: Optional[str] = None, limit: int = 5):
        return await self.recall_relevant_context(query=query, user_id=user_id, session_id=conversation_id, limit=limit)

    async def learn_user_preferences(self, user_id: str, interactions: List[Dict]):
        """Basic preference learning placeholder."""
        return {'learned': True, 'interactions_count': len(interactions)}

    # ---------------- Internal Helpers ---------------- #
    def _index_record(self, user_id: str, record: Dict[str, Any]):
        try:
            if self.use_chroma:
                col = self._get_chroma_collection(user_id)
                if not col:
                    return
                doc_id = record.get('id') or f"{record.get('session_id','sess')}:{record.get('timestamp')}:{len(record.get('content',''))}"
                col.add(ids=[doc_id], documents=[record.get('content','')], metadatas=[{
                    'session_id': record.get('session_id'),
                    'role': record.get('role'),
                    'intent': record.get('intent')
                }])
                # Persist periodically if persistent
                if self.config.get('chroma_persist_dir') and hasattr(self.chroma_client, 'persist'):
                    try:
                        self.chroma_client.persist()  # type: ignore
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Index record failed: {e}")

    def _prune_old(self, user_id: str):
        """Remove items older than max_age_seconds (if configured)."""
        max_age_seconds = self.config.get('max_age_seconds')
        if not max_age_seconds:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        def parse_ts(ts: str):
            try:
                return datetime.fromisoformat(ts.replace('Z','+00:00'))
            except Exception:
                return datetime.now(timezone.utc)
        history = self.conversation_cache.get(user_id, [])
        new_hist = [rec for rec in history if parse_ts(rec.get('timestamp','')) >= cutoff]
        if len(new_hist) != len(history):
            self.conversation_cache[user_id] = new_hist
            logger.debug(f"Pruned {len(history)-len(new_hist)} old records for user {user_id}")

# Global instance
minimal_semantic_memory_engine = MinimalSemanticMemoryEngine()

async def get_semantic_memory_engine(config: Optional[Dict[str, Any]] = None, 
                                   conversation_db: Any = None):
    """Get the minimal semantic memory engine instance"""
    if config:
        minimal_semantic_memory_engine.config.update(config)
        # Re-evaluate backend choices if config changed
        minimal_semantic_memory_engine.enable_embeddings = minimal_semantic_memory_engine.config.get("enable_embeddings", True)
        if minimal_semantic_memory_engine.enable_embeddings and not minimal_semantic_memory_engine.use_chroma:
            minimal_semantic_memory_engine._maybe_initialize_vector_backends()
    
    return minimal_semantic_memory_engine
