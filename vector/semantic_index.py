"""Semantic vector index stub.

Phase 1 provides optional in-memory embedding storage using sentence-transformers
if available. Later phases: persistence, ANN (FAISS), versioned embeddings.
"""
from __future__ import annotations
from typing import List, Tuple
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    MODEL_AVAILABLE = True
except Exception:
    MODEL_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    np = None  # type: ignore


class SemanticIndex:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist: bool = False, mongo_client=None, db_name: str = "buddy_vectors"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name) if MODEL_AVAILABLE else None
        self.texts: List[str] = []
        self.embeddings = None
        self.persist = persist and mongo_client is not None
        self.mongo = None
        if self.persist:
            self.mongo = mongo_client[db_name]
            self.collection = self.mongo["embeddings"]

    def add(self, text: str):
        self.texts.append(text)
        if self.model:
            emb = self.model.encode(self.texts, convert_to_numpy=True)
            self.embeddings = emb
        if self.persist and self.mongo:
            try:
                vec = None
                if self.model:
                    import numpy as np
                    vec = self.model.encode([text], convert_to_numpy=True)[0].tolist()
                self.collection.insert_one({"text": text, "vector": vec, "ts": datetime.utcnow()})
            except Exception:
                pass

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.model or self.embeddings is None:
            return []
        q_emb = self.model.encode([query], convert_to_numpy=True)[0]
        sims = (self.embeddings @ q_emb) / (
            (self.embeddings**2).sum(axis=1) ** 0.5 * (q_emb**2).sum() ** 0.5
        )
        idxs = sims.argsort()[-top_k:][::-1]
        return [(self.texts[i], float(sims[i])) for i in idxs]


semantic_index = SemanticIndex()
