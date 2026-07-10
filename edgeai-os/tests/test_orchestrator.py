from agents import REGISTRY, PRIMARY_AGENTS, SUPPORTING_AGENTS
from backend.core.orchestrator import Orchestrator


def test_primary_agents_match_ps8_brief():
    """The 5 agents PS8 names explicitly in 'What You May Build'."""
    names = {a.name for a in PRIMARY_AGENTS}
    assert names == {
        "ingestion", "knowledge", "maintenance", "compliance", "lessons_learned",
    }


def test_all_agents_registered():
    names = {a.name for a in REGISTRY}
    expected = {
        "ingestion", "knowledge", "maintenance", "compliance", "lessons_learned",
        "planner", "vision", "reasoning", "forecasting", "monitoring",
        "reporting", "notification",
    }
    assert names == expected
    assert len(REGISTRY) == len(PRIMARY_AGENTS) + len(SUPPORTING_AGENTS)


def test_dispatch_returns_response():
    orch = Orchestrator()
    response = orch.dispatch("ingestion", "ingest maintenance manual PDF")
    assert response.agent_name == "ingestion"
    assert "ingest maintenance manual PDF" in response.result


def test_handle_routes_and_dispatches():
    orch = Orchestrator()
    responses = orch.handle("compliance")
    assert len(responses) >= 1
    assert any(r.agent_name == "compliance" for r in responses)


def test_memory_persists_across_calls():
    orch = Orchestrator()
    orch.dispatch("knowledge", "query one")
    orch.dispatch("knowledge", "query two")
    recent = orch.memory.recent(2)
    assert len(recent) == 2
    assert recent[0]["task"] == "query one"
