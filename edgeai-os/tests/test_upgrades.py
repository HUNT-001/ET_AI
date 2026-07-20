"""
Tests for the enterprise upgrades: env-gated embedding + graph backends (with
safe fallbacks), OCR availability, and the document-upload endpoint. These
assert the *default zero-setup* behavior and that misconfiguration degrades
gracefully rather than crashing.
"""

import os

import pytest

from knowledge.vector_store import make_embedding_function
from knowledge import graph_store_neo4j
from knowledge.pdf_extract import _ocr_available


def test_embedding_factory_defaults_to_offline():
    assert make_embedding_function().name() == "offline_hashing_embedding"


def test_embedding_factory_falls_back_when_ollama_unreachable(monkeypatch):
    monkeypatch.setenv("EDGEAI_EMBED", "ollama")
    monkeypatch.setenv("EDGEAI_OLLAMA_HOST", "http://127.0.0.1:1")  # nothing listening
    # Should not raise — falls back to the offline embedder.
    assert make_embedding_function().name() == "offline_hashing_embedding"


def test_graph_defaults_to_in_memory():
    from knowledge.store import knowledge_graph
    from knowledge.graph_store import KnowledgeGraph
    assert isinstance(knowledge_graph, KnowledgeGraph)


def test_neo4j_backend_has_full_interface():
    # The Neo4j graph must implement the same methods as the in-memory one so
    # it's a true drop-in (no connection is made here).
    required = ["add_entity", "add_relationship", "entities_in_document",
                "find_entities", "related_entities", "all_entities",
                "cross_document_entities", "stats", "save"]
    assert all(hasattr(graph_store_neo4j.Neo4jKnowledgeGraph, m) for m in required)


def test_ocr_available_returns_bool():
    assert isinstance(_ocr_available(), bool)


def test_upload_endpoint_ingests_pdf():
    from fastapi.testclient import TestClient
    from backend.main import app

    sample = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                          "sample_maintenance_report.pdf")
    client = TestClient(app)
    with open(sample, "rb") as f:
        resp = client.post("/ingest/upload", files={"file": ("uploaded.pdf", f, "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_doc"] == "uploaded.pdf"
    assert body["chunks_created"] > 0
    assert body["entities_found"].get("equipment_tag", 0) > 0
