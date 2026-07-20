"""
Process-wide shared instances so IngestionAgent writes and KnowledgeAgent
reads from the same graph + vector store within one running backend.

Backends are selected from environment variables, defaulting to zero-setup
in-memory / offline implementations so the platform always runs out of the box:

  EDGEAI_GRAPH=neo4j   + NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD  → Neo4j graph
  EDGEAI_EMBED=ollama  + EDGEAI_OLLAMA_EMBED_MODEL / _HOST         → Ollama embeddings
                         (handled inside knowledge/vector_store.py)

If a configured backend can't be reached, we log and fall back rather than
crash — so a missing Neo4j/Ollama never takes the whole platform down.
"""

from __future__ import annotations

import os

from knowledge.graph_store import KnowledgeGraph
from knowledge.vector_store import VectorStore


def _make_graph():
    if os.environ.get("EDGEAI_GRAPH", "").lower() == "neo4j":
        try:
            from knowledge.graph_store_neo4j import Neo4jKnowledgeGraph

            graph = Neo4jKnowledgeGraph(
                os.environ["NEO4J_URI"],
                os.environ["NEO4J_USER"],
                os.environ["NEO4J_PASSWORD"],
                os.environ.get("NEO4J_DATABASE"),
            )
            print("[store] Using Neo4j-backed knowledge graph.")
            return graph
        except Exception as e:
            print(f"[store] Neo4j unavailable ({e}); using in-memory networkx graph.")
    return KnowledgeGraph()


knowledge_graph = _make_graph()
vector_store = VectorStore()
