"""
Vector store wrapper around ChromaDB with HYBRID retrieval: semantic (embedding
similarity) fused with lexical BM25 via Reciprocal Rank Fusion (RRF).

Why hybrid: industrial queries are full of exact tokens — equipment tags
(P-101A), standard codes (OISD-STD-118), units — where pure vector search
underperforms and lexical search shines; conversely, paraphrased questions need
semantics. RRF combines both rankings robustly without score normalization.

Embeddings: offline HashingVectorizer by default (zero setup, no downloads),
or local Ollama embeddings via EDGEAI_EMBED=ollama (privacy-first, better
recall). BM25 is pure-Python (rank_bm25) with a keyword-overlap fallback if the
package is absent — so retrieval never hard-fails.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from sklearn.feature_extraction.text import HashingVectorizer


# ---------------------------------------------------------------- embeddings
class OfflineHashingEmbeddingFunction(EmbeddingFunction):
    """Deterministic, fully offline embedding -- no model download required."""

    def __init__(self, n_features: int = 384):
        self._vectorizer = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2")

    def __call__(self, input: Documents) -> Embeddings:
        return self._vectorizer.transform(input).toarray().tolist()

    @staticmethod
    def name() -> str:
        return "offline_hashing_embedding"

    def get_config(self) -> dict:
        return {"n_features": self._vectorizer.n_features}

    @classmethod
    def build_from_config(cls, config: dict) -> "OfflineHashingEmbeddingFunction":
        return cls(n_features=config.get("n_features", 384))


class OllamaEmbeddingFunction(EmbeddingFunction):
    """Local, private embeddings via a running Ollama server (no data egress).
    Requires `ollama pull nomic-embed-text` and the Ollama daemon."""

    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def __call__(self, input: Documents) -> Embeddings:
        import requests

        out: list[list[float]] = []
        for text in input:
            r = requests.post(f"{self.host}/api/embeddings",
                              json={"model": self.model, "prompt": text}, timeout=60)
            r.raise_for_status()
            out.append(r.json()["embedding"])
        return out

    @staticmethod
    def name() -> str:
        return "ollama_embedding"

    def get_config(self) -> dict:
        return {"model": self.model, "host": self.host}

    @classmethod
    def build_from_config(cls, config: dict) -> "OllamaEmbeddingFunction":
        return cls(config.get("model", "nomic-embed-text"), config.get("host", "http://localhost:11434"))


def make_embedding_function():
    """Select the embedding backend from env, defaulting to offline hashing so
    the platform runs with zero setup. EDGEAI_EMBED=ollama opts into local
    Ollama embeddings; unreachable Ollama falls back to offline."""
    if os.environ.get("EDGEAI_EMBED", "").lower() == "ollama":
        try:
            fn = OllamaEmbeddingFunction(
                os.environ.get("EDGEAI_OLLAMA_EMBED_MODEL", "nomic-embed-text"),
                os.environ.get("EDGEAI_OLLAMA_HOST", "http://localhost:11434"),
            )
            fn(["healthcheck"])
            return fn
        except Exception as e:
            print(f"[vector_store] Ollama embeddings unavailable ({e}); using offline hashing embeddings.")
    return OfflineHashingEmbeddingFunction()


# ---------------------------------------------------------------- results
@dataclass
class SearchResult:
    text: str
    source_doc: str
    page: int
    similarity: float          # fused 0..1 score (higher is better)
    metadata: dict
    retrieval: str = "hybrid"  # "vector" | "bm25" | "hybrid"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9\-]+", text.lower())


# ---------------------------------------------------------------- store
class VectorStore:
    def __init__(self, persist_dir: str = "./vector_db/store", collection_name: str = "industrial_knowledge"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        embed_fn = make_embedding_function()
        # Namespace the collection by embedding type: hashing (384-dim) and
        # Ollama (768-dim) vectors must never share one collection.
        self.collection = self.client.get_or_create_collection(
            f"{collection_name}_{embed_fn.name()}", embedding_function=embed_fn
        )
        # Parallel corpus for BM25 (rebuilt from Chroma so it survives restarts).
        self._ids: list[str] = []
        self._corpus: list[dict] = []
        self._bm25 = None
        self._load_corpus()

    # ---- BM25 corpus management ----
    def _load_corpus(self) -> None:
        try:
            got = self.collection.get(include=["documents", "metadatas"])
            ids = got.get("ids", []) or []
            docs = got.get("documents", []) or []
            metas = got.get("metadatas", []) or []
            self._ids = list(ids)
            self._corpus = [
                {"text": d, "source_doc": (m or {}).get("source_doc", "unknown"),
                 "page": (m or {}).get("page", -1), "metadata": m or {}}
                for d, m in zip(docs, metas)
            ]
        except Exception:
            self._ids, self._corpus = [], []
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        self._bm25 = None
        if not self._corpus:
            return
        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi([_tokenize(c["text"]) for c in self._corpus])
        except Exception:
            self._bm25 = None  # fall back to keyword overlap in _bm25_rank

    def add_chunks(self, chunks: list[str], source_doc: str, page_numbers: list[int],
                   extra_metadata: list[dict] | None = None) -> None:
        base = len(self._ids)
        ids, metadatas = [], []
        for i in range(len(chunks)):
            cid = f"{source_doc}::chunk::{base + i}"
            meta = {"source_doc": source_doc, "page": page_numbers[i]}
            if extra_metadata:
                meta.update(extra_metadata[i])
            ids.append(cid)
            metadatas.append(meta)
            self._ids.append(cid)
            self._corpus.append({"text": chunks[i], "source_doc": source_doc,
                                 "page": page_numbers[i], "metadata": meta})
        self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        self._rebuild_bm25()

    # ---- ranking ----
    def _vector_rank(self, query: str, k: int) -> list[str]:
        res = self.collection.query(query_texts=[query], n_results=k)
        return (res.get("ids", [[]])[0]) or []

    def _bm25_rank(self, query: str, k: int) -> list[str]:
        if not self._corpus:
            return []
        q = _tokenize(query)
        if self._bm25 is not None:
            scores = self._bm25.get_scores(q)
        else:
            qset = set(q)
            scores = [len(qset & set(_tokenize(c["text"]))) for c in self._corpus]
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self._ids[i] for i in order[:k] if scores[i] > 0]

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60) -> list[SearchResult]:
        """Hybrid search: fuse vector and BM25 rankings via Reciprocal Rank
        Fusion. `similarity` is the RRF score scaled to ~0..1."""
        pool = max(top_k * 4, 10)
        vec = self._vector_rank(query, pool)
        lex = self._bm25_rank(query, pool)

        by_id = {cid: c for cid, c in zip(self._ids, self._corpus)}
        fused: dict[str, float] = {}
        seen_in: dict[str, set] = {}
        for rank, cid in enumerate(vec):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank)
            seen_in.setdefault(cid, set()).add("vector")
        for rank, cid in enumerate(lex):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank)
            seen_in.setdefault(cid, set()).add("bm25")

        if not fused:  # nothing retrieved
            return []
        max_score = max(fused.values()) or 1.0
        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

        out: list[SearchResult] = []
        for cid, score in ordered:
            c = by_id.get(cid)
            if not c:
                continue
            tags = seen_in.get(cid, set())
            retr = "hybrid" if len(tags) > 1 else next(iter(tags), "vector")
            out.append(SearchResult(
                text=c["text"], source_doc=c["source_doc"], page=c["page"],
                similarity=round(score / max_score, 4), metadata=c["metadata"], retrieval=retr,
            ))
        return out
