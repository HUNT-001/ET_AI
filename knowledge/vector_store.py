"""
Vector store wrapper around ChromaDB (embedded, no server needed for MVP --
matches PS8's suggested tech list). Provides hybrid search: semantic
(embedding similarity) + a simple keyword overlap re-ranking boost, which
is a reasonable stand-in for full BM25 hybrid search until that's needed.

IMPORTANT: uses a HashingVectorizer-based embedding function, NOT
Chroma's default (which downloads an ONNX model from the internet on
first use -- this fails on restricted-egress networks, including
corporate firewalls and this sandbox). HashingVectorizer works fully
offline. It's a weaker semantic signal than a real sentence-transformer
model, but real, deterministic, and won't silently break on a locked-down
network. Swap in a downloaded/local embedding model (e.g. via Ollama or
a pre-bundled sentence-transformers checkpoint) once that's available in
your deployment environment -- only this file needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from sklearn.feature_extraction.text import HashingVectorizer


class OfflineHashingEmbeddingFunction(EmbeddingFunction):
    """Deterministic, fully offline embedding -- no model download required."""

    def __init__(self, n_features: int = 384):
        self._vectorizer = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2")

    def __call__(self, input: Documents) -> Embeddings:
        matrix = self._vectorizer.transform(input)
        return matrix.toarray().tolist()

    @staticmethod
    def name() -> str:
        return "offline_hashing_embedding"

    def get_config(self) -> dict:
        # Required by newer ChromaDB versions for (de)serialising the
        # embedding function with a collection. n_features is the only
        # parameter that affects vector shape.
        return {"n_features": self._vectorizer.n_features}

    @classmethod
    def build_from_config(cls, config: dict) -> "OfflineHashingEmbeddingFunction":
        return cls(n_features=config.get("n_features", 384))


@dataclass
class SearchResult:
    text: str
    source_doc: str
    page: int
    similarity: float   # 0..1, higher is better
    metadata: dict


class VectorStore:
    def __init__(self, persist_dir: str = "./vector_db/store", collection_name: str = "industrial_knowledge"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            collection_name, embedding_function=OfflineHashingEmbeddingFunction()
        )

    def add_chunks(self, chunks: list[str], source_doc: str, page_numbers: list[int], extra_metadata: list[dict] | None = None) -> None:
        ids = [f"{source_doc}::chunk::{i}" for i in range(len(chunks))]
        metadatas = []
        for i in range(len(chunks)):
            meta = {"source_doc": source_doc, "page": page_numbers[i]}
            if extra_metadata:
                meta.update(extra_metadata[i])
            metadatas.append(meta)
        self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        out: list[SearchResult] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            similarity = 1.0 / (1.0 + dist)  # convert distance to a 0..1-ish similarity
            keyword_boost = _keyword_overlap_score(query, doc)
            out.append(SearchResult(
                text=doc,
                source_doc=meta.get("source_doc", "unknown"),
                page=meta.get("page", -1),
                similarity=round(min(1.0, similarity + 0.1 * keyword_boost), 4),
                metadata=meta,
            ))
        out.sort(key=lambda r: r.similarity, reverse=True)
        return out


def _keyword_overlap_score(query: str, text: str) -> float:
    q_words = set(query.lower().split())
    t_words = set(text.lower().split())
    if not q_words:
        return 0.0
    return len(q_words & t_words) / len(q_words)
