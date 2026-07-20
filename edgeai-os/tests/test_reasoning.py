"""
Tests for the industrial reasoning layer: ontology + causal propagation,
temporal graph, episodic memory, the Reasoning Engine, and the what-if simulator.
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from agents import reasoning_engine as re_engine
from agents.simulation import simulate_failure
from knowledge import ontology
from knowledge.temporal import TemporalGraph
from backend.core.episodic import EpisodicMemory

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                      "sample_maintenance_report.pdf")


@pytest.fixture(scope="module", autouse=True)
def ingested():
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE}))
    re_engine.populate_episodes_from_corpus()
    yield


# ---- ontology / causal ----
def test_classify_equipment():
    assert ontology.classify_equipment("P-101A")["class"] == "pump"
    assert "rotating_equipment" in ontology.classify_equipment("P-101A")["is_a"]


def test_map_symptoms():
    s = ontology.map_symptoms("Vibration readings exceeded the baseline threshold by 18%")
    assert "vibration_elevated" in s


def test_causal_propagation_reaches_shutdown():
    out = ontology.propagate(["vibration_elevated"])
    assert out["terminal"] == "unplanned_shutdown"
    assert out["hours_to_terminal"] and out["hours_to_terminal"] > 0
    assert "seal failure" in ontology.describe_chain(out["primary_chain"])


# ---- temporal ----
def test_temporal_history_and_changes():
    g = TemporalGraph()
    g.record("P-101A", "vibration", "18% over", "14 March 2026", source="rep")
    g.record("P-101A", "vibration", "anomaly", "22 August 2025", source="log")
    hist = g.history("P-101A")
    assert len(hist) == 2 and hist[0]["date"].endswith("2025")  # sorted ascending
    assert g.recurrence("P-101A")["recurring"] is True
    changes = g.changes_between("01 January 2026", "31 December 2026")
    assert len(changes) == 1


# ---- episodic ----
def test_episodic_precedent():
    m = EpisodicMemory()
    m.record("P-101A", "vibration", "22 August 2025", resolution="re-torqued foundation bolt")
    m.record("P-101A", "vibration", "22 August 2025", resolution="re-torqued foundation bolt")  # dup ignored
    p = m.precedent("P-101A")
    assert p["seen_before"] and p["occurrences"] == 1
    assert p["prior_resolutions"]


# ---- reasoning engine ----
def test_reasoning_engine_produces_operational_assessment():
    out = re_engine.reason("P-101A")
    assert out["equipment_tag"] == "P-101A"
    assert out["equipment_class"]["class"] == "pump"
    assert out["causal_chain"]
    assert out["hours_to_elevated_risk"] is not None
    assert "recommend" in out["recommendation"].lower() or out["recommendation"]
    # Narrative reads as operational intelligence, not just retrieval.
    assert any(w in out["narrative"].lower() for w in ["risk", "shutdown", "schedule"])


# ---- simulator ----
def test_what_if_simulator():
    out = simulate_failure("P-101A")
    assert out["equipment_tag"] == "P-101A"
    assert out["downtime_hours"] > 0
    assert out["projected_failure"]
    assert out["narrative"]
