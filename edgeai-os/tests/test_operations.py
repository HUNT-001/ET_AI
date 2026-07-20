"""
Tests for the operational capabilities: workflow engine (work orders + human
approval + audit), P&ID vision pipeline, and the simulated sensor stream.
(Neo4j live coverage is in test_neo4j_live.py, which self-skips without a server.)
"""

import os

import pytest

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from backend.core.workflow import WorkflowEngine
from backend.core.sensor_stream import SensorStream

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                      "sample_maintenance_report.pdf")
SAMPLE_PID = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                          "sample_pid.png")


@pytest.fixture(scope="module", autouse=True)
def ingested():
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE}))
    yield


# ---- workflow engine ----
def _assessment():
    return {"equipment_tag": "P-101A", "risk": {"level": "high", "risk": 0.9},
            "recommendation": "Bearing replacement on P-101A",
            "recommended_part": "bearing assembly",
            "hours_to_elevated_risk": 6, "narrative": "test"}


def test_work_order_held_for_approval():
    eng = WorkflowEngine()
    wo = eng.create_from_assessment(_assessment())
    assert wo["status"] == "pending_approval"
    assert wo["id"].startswith("WO-")
    # Nothing executed yet: only the creation audit entry.
    assert [a["event"] for a in wo["audit"]] == ["created"]


def test_work_order_executes_on_approval_with_audit():
    eng = WorkflowEngine(notifier=lambda t, m, s: {"recipients": ["maintenance_lead"]})
    wo = eng.create_from_assessment(_assessment())
    done = eng.approve(wo["id"], approver="pavan")
    assert done["status"] == "executed"
    events = [a["event"] for a in done["audit"]]
    assert events == ["created", "approved", "notified", "parts_reserved", "cmms_handoff", "executed"]
    assert done["external_ref"].startswith("CMMS-")


def test_work_order_reject_blocks_execution():
    eng = WorkflowEngine()
    wo = eng.create_from_assessment(_assessment())
    rej = eng.reject(wo["id"], reason="schedule conflict")
    assert rej["status"] == "rejected"
    # Approving a rejected order fails cleanly.
    out = eng.approve(wo["id"])
    assert "error" in out


# ---- P&ID vision ----
def test_pid_vision_extracts_tags_and_symbols():
    cv2 = pytest.importorskip("cv2")
    if not os.path.exists(SAMPLE_PID):
        import subprocess, sys
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..",
                        "scripts", "generate_sample_pid.py")], check=True)
    from knowledge.pid_vision import analyze_pid

    r = analyze_pid(SAMPLE_PID)
    assert r["symbols"]["circles"] >= 1
    assert r["piping_lines"] >= 1
    if r["ocr_used"]:
        assert "P-101A" in r["equipment_tags"]
        assert "DWG-PID-0007" not in r["equipment_tags"]  # drawing no. excluded


def test_vision_agent_writes_graph():
    pytest.importorskip("cv2")
    from agents.vision_agent import VisionAgent
    from knowledge.store import knowledge_graph

    r = VisionAgent().run(AgentRequest(task="parse", payload={"path": SAMPLE_PID}))
    assert r.result is not None
    if r.result["ocr_used"] and r.result["equipment_tags"]:
        found = knowledge_graph.find_entities(entity_type="equipment_tag", value_contains="T-300")
        assert found


# ---- sensor stream ----
def test_sensor_stream_degrades_to_anomaly():
    s = SensorStream(seed=7)
    last = None
    for _ in range(40):
        last = s.tick("P-101A", degrade=True)
    assert last["simulated"] is True
    assert last["anomaly"] is True          # degradation scenario must trip
    assert last["readings"]["temperature_c"] > 60


def test_sensor_stream_stable_stays_normal():
    s = SensorStream(seed=7)
    last = None
    for _ in range(15):
        last = s.tick("V-204", degrade=False)
    assert last["anomaly"] is False
