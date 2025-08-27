"""Semantic vector index stub.

Phase 1 provides optional in-memory embedding storage using sentence-transformers
if available. Later phases: persistence, ANN (FAISS), versioned embeddings.
"""
from __future__ import annotations
from typing import List, Tuple, Optional, Dict
from collections import Counter
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
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", persist: bool = False, mongo_client=None, db_name: str = "buddy_vectors", chunk_size: int = 800, overlap: int = 80):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name) if MODEL_AVAILABLE and SentenceTransformer else None
        self.texts: List[str] = []
        self.metas: List[Dict] = []  # parallel metadata list
        self.embeddings = None
        self.persist = persist and mongo_client is not None
        self.mongo = None
        self.chunk_size = chunk_size
        self.overlap = overlap
        if self.persist and mongo_client is not None:
            self.mongo = mongo_client[db_name]
            self.collection = self.mongo["embeddings"]

    def _chunk(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks = []
        step = self.chunk_size - self.overlap
        for i in range(0, len(text), step):
            chunk = text[i:i+self.chunk_size]
            if chunk:
                chunks.append(chunk)
            if i + self.chunk_size >= len(text):
                break
        return chunks

    def add(self, text: str, metadata: Optional[Dict] = None):
        meta = metadata or {}
        to_add = self._chunk(text)
        for chunk in to_add:
            self.texts.append(chunk)
            self.metas.append(meta)
            if self.model:
                emb = self.model.encode(self.texts, convert_to_numpy=True)
                self.embeddings = emb
            if self.persist and self.mongo:
                try:
                    vec = None
                    if self.model:
                        import numpy as np
                        vec = self.model.encode([chunk], convert_to_numpy=True)[0].tolist()
                    self.collection.insert_one({"text": chunk, "vector": vec, "meta": meta, "ts": datetime.utcnow()})
                except Exception:
                    pass

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.model or self.embeddings is None:
            # fallback to persisted raw vectors if exist
            if self.persist and self.mongo:
                try:
                    docs = list(self.collection.find().sort("ts", -1).limit(200))
                    if not docs:
                        return []
                    import numpy as np
                    q_emb = self.model.encode([query], convert_to_numpy=True)[0] if self.model else None
                    if q_emb is None:
                        return []
                    scored = []
                    for d in docs:
                        vec = d.get("vector")
                        text = d.get("text")
                        if vec and text:
                            v = np.array(vec)
                            sim = float((v @ q_emb) / ((v**2).sum() ** 0.5 * (q_emb**2).sum() ** 0.5))
                            scored.append((text, sim))
                    scored.sort(key=lambda x: x[1], reverse=True)
                    return scored[:top_k]
                except Exception:
                    return []
            return []
        q_emb = self.model.encode([query], convert_to_numpy=True)[0]
        sims = (self.embeddings @ q_emb) / (
            (self.embeddings**2).sum(axis=1) ** 0.5 * (q_emb**2).sum() ** 0.5
        )
        idxs = sims.argsort()[-top_k:][::-1]
        return [(self.texts[i], float(sims[i])) for i in idxs]

    # New advanced search returning metadata and allowing simple equality filters
    def search_with_meta(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:  # type: ignore[name-defined]
        if metadata_filter:
            candidate_indices = [i for i, m in enumerate(self.metas) if all(m.get(k) == v for k, v in metadata_filter.items())]
        else:
            candidate_indices = list(range(len(self.texts)))
        if not candidate_indices:
            return []
        if not self.model or self.embeddings is None:
            # naive fallback: keyword overlap score
            q_words = set(query.lower().split())
            scored = []
            for i in candidate_indices:
                words = set(self.texts[i].lower().split())
                overlap = len(q_words & words)
                if overlap:
                    scored.append((i, overlap))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = []
            for idx, sc in scored[:top_k]:
                results.append({"text": self.texts[idx], "score": float(sc), "metadata": self.metas[idx]})
            return results
        # vector path
        import numpy as np  # type: ignore
        q_emb = self.model.encode([query], convert_to_numpy=True)[0]
        sub_embs = np.array([self.embeddings[i] for i in candidate_indices])
        sims = (sub_embs @ q_emb) / ((sub_embs**2).sum(axis=1) ** 0.5 * (q_emb**2).sum() ** 0.5)
        order = sims.argsort()[::-1][:top_k]
        results = []
        for pos in order:
            orig_idx = candidate_indices[int(pos)]
            results.append({"text": self.texts[orig_idx], "score": float(sims[pos]), "metadata": self.metas[orig_idx]})
        return results


class BowVectorIndex:
    """Lightweight bag-of-words cosine similarity backend (no external deps).

    Optional persistence if a mongo_client is provided (schema: {text, bow, meta, ts}).
    """
    def __init__(self, mongo_client=None, db_name: str = "buddy_vectors"):
        self.texts: List[str] = []
        self.vectors: List[Counter] = []
        self.mongo = None
        if mongo_client is not None:
            try:
                self.mongo = mongo_client[db_name]
                self.collection = self.mongo["bow_embeddings"]
            except Exception:
                self.mongo = None

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in text.lower().split() if t]

    def add(self, text: str, metadata: Optional[Dict] = None):  # metadata optional
        bow = Counter(self._tokenize(text))
        self.texts.append(text)
        self.vectors.append(bow)
        if self.mongo:
            try:
                self.collection.insert_one({"text": text, "bow": dict(bow), "meta": metadata or {}, "ts": datetime.utcnow()})
            except Exception:
                pass

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.texts and self.mongo:
            # lazy load a small sample from persistence
            try:
                docs = list(self.collection.find().sort("ts", -1).limit(500))
                for d in docs:
                    self.texts.append(d.get("text", ""))
                    self.vectors.append(Counter(d.get("bow", {})))
            except Exception:
                pass
        if not self.texts:
            return []
        q_vec = Counter(self._tokenize(query))
        def cosine(a: Counter, b: Counter) -> float:
            if not a or not b:
                return 0.0
            common = set(a) & set(b)
            num = sum(a[t] * b[t] for t in common)
            den_a = sum(v*v for v in a.values()) ** 0.5
            den_b = sum(v*v for v in b.values()) ** 0.5
            if den_a == 0 or den_b == 0:
                return 0.0
            return num / (den_a * den_b)
        scored = [(self.texts[i], cosine(q_vec, self.vectors[i])) for i in range(len(self.texts))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


semantic_index = SemanticIndex()


class FaissIndex:
    """FAISS adapter stub (requires faiss library)."""
    def __init__(self):
        try:
            import faiss  # type: ignore
            self.faiss = faiss
        except Exception:
            self.faiss = None
        self.texts: List[str] = []
        self.dim = 384
        self.index = None
        if MODEL_AVAILABLE and self.faiss:
            self.index = self.faiss.IndexFlatIP(self.dim)  # type: ignore
        self.model = SentenceTransformer("all-MiniLM-L6-v2") if MODEL_AVAILABLE and SentenceTransformer else None

    def add(self, text: str, metadata: Optional[Dict] = None):
        if not self.model or not self.index:
            return
        vec = self.model.encode([text], convert_to_numpy=True)
        if vec is None:
            return
        self.index.add(vec)  # type: ignore
        self.texts.append(text)

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.model or not self.index or not self.texts:
            return []
        q = self.model.encode([query], convert_to_numpy=True)
        D, I = self.index.search(q, min(top_k, len(self.texts)))  # type: ignore
        results: List[Tuple[str, float]] = []
        for score, idx in zip(D[0].tolist(), I[0].tolist()):  # type: ignore
            if 0 <= idx < len(self.texts):
                results.append((self.texts[idx], float(score)))
        return results


class ChromaIndex:
    """ChromaDB adapter stub (requires chromadb)."""
    def __init__(self, collection: str = "buddy"):
        try:
            import chromadb  # type: ignore
            self.client = chromadb.Client()  # type: ignore
            self.collection = self.client.get_or_create_collection(collection_name=collection)  # type: ignore
        except Exception:
            self.client = None
            self.collection = None

    def add(self, text: str, metadata: Optional[Dict] = None):
        if not self.collection:
            return
        doc_id = f"doc_{len(self.collection.get()['ids'])}" if self.collection else "doc"
        try:
            self.collection.add(ids=[doc_id], documents=[text], metadatas=[metadata or {}])  # type: ignore
        except Exception:
            pass

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.collection:
            return []
        try:
            res = self.collection.query(query_texts=[query], n_results=top_k)  # type: ignore
            docs = res.get('documents', [[]])[0]
            scores = res.get('distances', [[]])[0]
            return list(zip(docs, scores))  # type: ignore
        except Exception:
            return []
