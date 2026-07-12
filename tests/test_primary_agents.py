"""
End-to-end tests for the now-REAL primary agents (Maintenance, Compliance,
Lessons Learned) and the synthesis path in KnowledgeAgent. All run against
the ingested synthetic sample report — no external LLM required (offline
deterministic synthesis).
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.compliance_agent import ComplianceAgent
from agents.lessons_learned_agent import LessonsLearnedAgent
from agents.forecasting_agent import score_degradation
from agents.reasoning_agent import Passage, synthesize

SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__), "..", "datasets", "samples", "sample_maintenance_report.pdf"
)


@pytest.fixture(scope="module", autouse=True)
def ingested_sample():
    agent = IngestionAgent()
    resp = agent.run(AgentRequest(task="ingest", payload={"path": SAMPLE_PDF}))
    assert resp.confidence == 1.0, resp.notes
    yield resp


def test_knowledge_agent_synthesizes_cited_answer():
    agent = KnowledgeAgent()
    resp = agent.run(AgentRequest(task="knowledge", payload={"query": "P-101A bearing vibration"}))
    assert resp.confidence > 0
    # Synthesized (not the old "[extractive, LLM synthesis not yet wired]" stub).
    assert "not yet wired" not in resp.result
    assert "synthesis_mode" in resp.notes
    assert "P-101A" in resp.result or "bearing" in resp.result.lower()


def test_reasoning_offline_synthesis_adds_citations():
    passages = [
        Passage(text="Vibration on P-101A exceeded baseline by 18%.", source_doc="/x/rep.pdf", page=1, similarity=0.7),
    ]
    out = synthesize("vibration on P-101A", passages)
    assert out["mode"] == "offline"
    assert "rep.pdf" in out["answer"]
    assert out["citations"][0]["source_doc"] == "rep.pdf"


def test_forecasting_flags_high_risk_on_degradation_text():
    text = ("Vibration readings on P-101A exceeded the baseline threshold by 18%. "
            "Bearing housing temperature reached 71 degrees Celsius above the 65 "
            "degree Celsius normal operating range. Given the recurrence pattern, "
            "bearing replacement is recommended.")
    out = score_degradation(text)
    assert out["risk"] > 0.3
    assert out["level"] in {"medium", "high"}
    assert len(out["factors"]) >= 2


def test_maintenance_agent_produces_rca_and_risk():
    agent = MaintenanceAgent()
    resp = agent.run(AgentRequest(task="maintenance", payload={"equipment_tag": "P-101A"}))
    assert resp.result["equipment_tag"] == "P-101A"
    assert resp.result["risk"]["level"] in {"low", "medium", "high"}
    assert resp.result["rca_narrative"]
    assert resp.result["citations"]


def test_maintenance_agent_needs_a_tag():
    agent = MaintenanceAgent()
    resp = agent.run(AgentRequest(task="maintenance", payload={}))
    assert resp.confidence == 0.0
    assert "equipment tag" in resp.notes.lower()


def test_compliance_agent_detects_coverage_gaps():
    agent = ComplianceAgent()
    resp = agent.run(AgentRequest(task="compliance", payload={"area": "North Sector Process Unit 3"}))
    # Sample references OISD + Factory Act, but not environmental/quality → gaps.
    assert "environmental_norms" in resp.result["coverage_gaps"]
    assert "quality_standards" in resp.result["coverage_gaps"]
    assert "OISD" in resp.result["frameworks_covered"]
    assert "Compliance Evidence Package" in resp.result["evidence_package"]


def test_lessons_learned_surfaces_recurrence_pattern():
    agent = LessonsLearnedAgent()
    resp = agent.run(AgentRequest(task="lessons_learned", payload={}))
    assert resp.result["patterns_found"] >= 1
    tags = [p["equipment_tag"] for p in resp.result["patterns"]]
    assert any("P-101A" in t for t in tags)
    # Every surfaced pattern should produce a routed notification.
    assert len(resp.result["notifications"]) == resp.result["patterns_found"]
