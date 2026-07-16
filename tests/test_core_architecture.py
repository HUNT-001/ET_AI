"""
Tests for the orchestration core: intent routing, PlannerAgent decomposition,
plan execution, cross-agent invocation through the Orchestrator, MemoryLayer
wiring, and MonitoringAgent anomaly detection.
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from agents.planner_agent import build_plan
from agents.monitoring_agent import detect_anomalies
from backend.core.orchestrator import Orchestrator
from knowledge.store import knowledge_graph, vector_store

SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "samples", "sample_maintenance_report.pdf"
)


@pytest.fixture(scope="module", autouse=True)
def ingested():
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE_PDF}))
    yield


# ---- routing ----
def test_routing_classifies_intents():
    orch = Orchestrator()
    assert orch.classify("Are there any open compliance gaps for Unit 3?") == "compliance"
    assert orch.classify("What is the root cause of the P-101A failure?") == "maintenance"
    assert orch.classify("Have we seen this failure pattern before?") == "lessons_learned"
    # A general question with no domain signal → Knowledge Copilot.
    assert orch.classify("Tell me about the pressure relief valve settings") == "knowledge"


def test_route_no_longer_needs_agent_name_in_task():
    orch = Orchestrator()
    # Old routing only matched when the task literally contained the agent name.
    assert orch.route("why did the bearing fail?") == ["maintenance"]


# ---- planner ----
def test_planner_decomposes_failure_goal():
    plan = build_plan("root cause of P-101A failure", {})
    agents = [s["agent"] for s in plan]
    assert agents == ["knowledge", "maintenance", "lessons_learned"]
    # The equipment tag is threaded into the maintenance step.
    maint = next(s for s in plan if s["agent"] == "maintenance")
    assert maint["payload"].get("equipment_tag") == "P-101A"


def test_planner_defaults_to_knowledge():
    plan = build_plan("what does OEM manual say about lubrication", {})
    assert [s["agent"] for s in plan] == ["knowledge"]


# ---- plan execution + memory wiring ----
def test_plan_and_execute_runs_chain_and_logs_incident():
    orch = Orchestrator()
    out = orch.plan_and_execute("root cause of P-101A failure")
    assert [s["agent"] for s in out["plan"]] == ["knowledge", "maintenance", "lessons_learned"]
    # Maintenance step produced a real risk assessment...
    maint = next(r for r in out["results"] if r["agent"] == "maintenance")
    assert maint["result"]["risk"]["level"] in {"medium", "high"}
    # ...and logged it to the shared incident archive (memory wiring).
    archive = orch.memory.snapshot()["incident_archive"]
    assert any(i["equipment_tag"] == "P-101A" for i in archive)


def test_lessons_learned_reads_memory_incidents():
    orch = Orchestrator()
    # Seed the incident archive via a maintenance run, then confirm Lessons
    # Learned folds it in (signal includes 'logged_incident').
    orch.dispatch("maintenance", "P-101A", {"equipment_tag": "P-101A"})
    resp = orch.dispatch("lessons_learned", "patterns", {"equipment_tag": "P-101A"})
    signals = " ".join(p["signal"] for p in resp.result["patterns"])
    assert "logged_incident" in signals


# ---- cross-agent invocation through the orchestrator ----
def test_knowledge_synthesis_runs_through_orchestrator():
    orch = Orchestrator()
    resp = orch.dispatch("knowledge", "q", {"query": "P-101A bearing vibration"})
    # Answer came back synthesized (Reasoning invoked via services), with a mode.
    assert resp.result and "not yet wired" not in str(resp.result)
    assert "synthesis_mode" in resp.notes


def test_maintenance_fuses_monitoring_anomaly():
    orch = Orchestrator()
    # Supply an anomalous reading series; risk should pick up a live-signal factor.
    resp = orch.dispatch("maintenance", "P-101A",
                         {"equipment_tag": "P-101A", "readings": [10, 10, 10, 10, 10, 48]})
    factors = " ".join(resp.result["risk"]["factors"])
    assert "anomaly" in factors.lower()
    assert resp.result["monitoring"]["anomaly"] is True


# ---- monitoring ----
def test_monitoring_detects_and_ignores():
    assert detect_anomalies([10, 10, 10, 10, 10, 50])["anomaly"] is True
    assert detect_anomalies([10, 10, 10])["anomaly"] is False   # flat, no variance
    assert detect_anomalies([1])["anomaly"] is False            # too few readings
