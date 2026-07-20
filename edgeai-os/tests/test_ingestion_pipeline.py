"""
End-to-end test for the REAL ingestion + retrieval pipeline (not stubs).
Ingests the synthetic sample PDF, then queries KnowledgeAgent and checks
that retrieval finds the relevant passage with a real citation.
"""

import os
import shutil

import pytest

from agents.ingestion_agent import IngestionAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.base import AgentRequest
from knowledge.store import knowledge_graph, vector_store

SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "samples", "sample_maintenance_report.pdf"
)


@pytest.fixture(scope="module", autouse=True)
def ingested_sample():
    """Ingest the sample PDF once for this test module."""
    agent = IngestionAgent()
    response = agent.run(AgentRequest(task="ingest", payload={"path": SAMPLE_PDF}))
    assert response.confidence == 1.0, response.notes
    yield response


def test_ingestion_extracts_entities(ingested_sample):
    entities = ingested_sample.result["entities_found"]
    assert entities.get("equipment_tag", 0) > 0
    assert entities.get("regulatory_reference", 0) > 0
    assert entities.get("date", 0) > 0


def test_knowledge_graph_has_entities():
    stats = knowledge_graph.stats()
    assert stats["total_entities"] > 0


def test_knowledge_agent_retrieves_relevant_passage():
    agent = KnowledgeAgent()
    response = agent.run(AgentRequest(task="knowledge", payload={"query": "P-101A bearing vibration"}))
    assert response.confidence > 0
    assert "P-101A" in response.result or "bearing" in response.result.lower()
    assert "sample_maintenance_report.pdf" in response.notes


def test_knowledge_agent_returns_citation_with_page():
    agent = KnowledgeAgent()
    response = agent.run(AgentRequest(task="knowledge", payload={"query": "regulatory compliance OISD"}))
    assert "source_doc" in response.notes
    assert "page" in response.notes
