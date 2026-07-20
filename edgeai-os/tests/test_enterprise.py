"""
Tests for the enterprise-runtime additions: observability traces, human-in-the-
loop approval policy, event-driven ingestion cascade, reflection auto-retry,
and the opt-in LangGraph runtime's safe fallback.
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from agents.reflection import answer_with_reflection
from backend.core.events import bus
from backend.core.orchestrator import Orchestrator
from backend.core.policy import approval_decision
from backend.core.trace import tracer
from backend.core.langgraph_runtime import langgraph_available
from knowledge.store import vector_store

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                      "sample_maintenance_report.pdf")


@pytest.fixture(scope="module", autouse=True)
def ingested():
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE}))
    yield


# ---- observability ----
def test_tracer_records_spans():
    orch = Orchestrator()
    orch.dispatch("compliance", "Unit 3", {"area": "Unit 3"})
    summary = tracer.summary()
    assert summary["total_spans"] > 0
    assert "compliance" in summary["by_agent"]
    assert summary["by_agent"]["compliance"]["avg_ms"] >= 0


# ---- human-in-the-loop policy ----
def test_approval_gate_holds_low_confidence():
    d = approval_decision(0.2, {"status": "verified", "flagged": []})
    assert d["requires_approval"] is True
    assert not d["auto_approved"]


def test_approval_gate_holds_unverified():
    d = approval_decision(0.9, {"status": "partial", "flagged": ["x"]})
    assert d["requires_approval"] is True


def test_approval_gate_auto_approves_confident_verified():
    d = approval_decision(0.8, {"status": "verified", "flagged": []})
    assert d["requires_approval"] is False
    assert d["auto_approved"] is True


# ---- event-driven cascade ----
def test_document_ingested_event_triggers_reactions():
    reactions = bus.publish("document_ingested", {"area": "Unit 3"})
    handlers = {r["handler"] for r in reactions}
    assert any("compliance" in h for h in handlers)
    assert any("lessons" in h for h in handlers)
    # Compliance reaction actually computed gaps.
    comp = next(r for r in reactions if "compliance" in r["handler"])
    assert "coverage_gaps" in comp["result"]


# ---- reflection ----
def test_reflection_returns_verified_or_reflected():
    out = answer_with_reflection("P-101A bearing vibration", vector_store.search, top_k=3)
    assert out["answer"]
    assert "status" in out["verification"]
    assert isinstance(out["reflected"], bool)
    assert out["attempts"] in (1, 2)


# ---- langgraph opt-in fallback ----
def test_langgraph_runtime_falls_back_when_absent(monkeypatch):
    monkeypatch.setenv("EDGEAI_RUNTIME", "langgraph")
    orch = Orchestrator()
    out = orch.plan_and_execute("root cause of P-101A failure")
    # Whether langgraph is installed or not, we get a coherent plan+results.
    assert "plan" in out and "results" in out
    if not langgraph_available():
        assert out["plan"]  # native fallback produced a plan
