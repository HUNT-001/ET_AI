"""
Tests for the MCP server tool logic (the *_impl functions) — exercised directly
without the MCP stdio runtime, so they run in CI without the `mcp` package.
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from integrations import mcp_server as m

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                      "sample_maintenance_report.pdf")


@pytest.fixture(scope="module", autouse=True)
def ingested():
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE}))
    yield


def test_ask_knowledge_impl_returns_cited_answer():
    out = m.ask_knowledge_impl("What did the inspection find about P-101A bearing?")
    assert out["answer"]
    assert out["citations"]
    assert "status" in out["verification"]


def test_equipment_risk_impl():
    out = m.equipment_risk_impl("P-101A")
    assert out["equipment_tag"] == "P-101A"
    assert out["risk"]["level"] in {"low", "medium", "high"}


def test_check_compliance_impl_finds_gaps():
    out = m.check_compliance_impl("North Sector Process Unit 3")
    assert "PESO" in out["coverage_gaps"]


def test_graph_stats_impl():
    out = m.graph_stats_impl()
    assert out["total_entities"] > 0


def test_tool_functions_registered_names():
    # The impl functions carry docstrings (used as MCP tool descriptions).
    for fn in [m.ask_knowledge_impl, m.equipment_risk_impl, m.check_compliance_impl,
               m.failure_patterns_impl, m.ingest_document_impl, m.graph_stats_impl]:
        assert fn.__doc__ and len(fn.__doc__) > 10
