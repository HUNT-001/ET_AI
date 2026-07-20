"""
Tests for the VerifierAgent (Generator→Supervisor grounding check): grounded
claims pass, fabricated/uncited claims are flagged and stripped.
"""

from agents.reasoning_agent import Passage
from agents.verifier_agent import verify_answer


def _passages():
    return [Passage(
        text=("Vibration on pump P-101A exceeded the baseline threshold by 18%, "
              "consistent with early-stage bearing wear. Bearing housing temperature "
              "reached 71 degrees Celsius above the 65 degree normal range."),
        source_doc="/x/report.pdf", page=1, similarity=0.7)]


def test_grounded_answer_passes():
    ans = ("Vibration on P-101A exceeded the baseline threshold by 18%, consistent "
           "with early-stage bearing wear. [report.pdf p.1]")
    r = verify_answer(ans, _passages())
    assert r["status"] == "verified"
    assert r["coverage"] == 1.0
    assert r["flagged"] == []


def test_fabricated_claim_is_flagged_and_stripped():
    ans = ("Vibration on P-101A exceeded the baseline threshold by 18%. [report.pdf p.1] "
           "The reactor core temperature is approaching a meltdown and the plant must "
           "evacuate immediately.")
    r = verify_answer(ans, _passages())
    # The invented, ungrounded second claim must be caught.
    assert r["status"] == "partial"
    assert any("meltdown" in f for f in r["flagged"])
    assert "meltdown" not in r["verified_answer"]
    assert r["grounded_claims"] < r["claims"]


def test_empty_answer_is_unverified():
    r = verify_answer("", _passages())
    assert r["status"] == "unverified"
    assert r["claims"] == 0


def test_verifier_agent_via_registry():
    from agents import AGENTS_BY_NAME
    from agents.base import AgentRequest
    agent = AGENTS_BY_NAME["verifier"]
    resp = agent.run(AgentRequest(task="v", payload={
        "answer": "Vibration on P-101A exceeded baseline by 18%. [report.pdf p.1]",
        "passages": [{"text": "Vibration on P-101A exceeded the baseline threshold by 18%.",
                      "source_doc": "/x/report.pdf", "page": 1, "similarity": 0.7}],
    }))
    assert resp.result["status"] in {"verified", "partial"}
    assert resp.agent_name == "verifier"
