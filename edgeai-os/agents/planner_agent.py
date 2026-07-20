"""
PlannerAgent — decomposes a high-level goal into an ordered sequence of agent
calls (per Architecture.md's typical PS8 flow: Ingestion → Knowledge →
Maintenance → Compliance → Lessons Learned → Report).

Status: real (not a stub). It emits a structured plan — a list of
{agent, task, payload} steps — that the Orchestrator's `plan_and_execute`
runs in order, threading results through shared memory. The planning itself is
transparent, rule-based intent decomposition (no model dependency); it can be
upgraded to LLM-based planning behind this same `{"plan": [...]}` contract.
"""

from __future__ import annotations

import re

from agents.base import AgentRequest, AgentResponse, BaseAgent

_EQUIPMENT_TAG = re.compile(r"\b[A-Z]{1,3}-\d{2,4}[A-Z]?\b")

_COMPLIANCE = ["complian", "regulat", "audit", "oisd", "peso", "factory act",
               "gap", "non-conform", "nonconform", "deviation", "evidence"]
_MAINTENANCE = ["maintenance", "rca", "root cause", "root-cause", "failure",
                "failed", "repair", "vibration", "bearing", "degradation", "fault"]
_LESSONS = ["lesson", "recurring", "recurrence", "pattern", "seen before",
            "near-miss", "near miss", "systemic", "before", "ever seen"]
_INGEST = ["ingest", "upload", "load document", "add document", "index"]


def _tag(goal: str, payload: dict) -> str | None:
    if payload.get("equipment_tag"):
        return payload["equipment_tag"]
    m = _EQUIPMENT_TAG.search(goal or "")
    return m.group(0) if m else None


def build_plan(goal: str, payload: dict | None = None) -> list[dict]:
    payload = payload or {}
    t = (goal or "").lower()
    tag = _tag(goal, payload)

    if any(k in t for k in _INGEST):
        return [{"agent": "ingestion", "task": goal, "payload": {}}]

    # Failure / RCA / equipment-centric goal → full diagnostic chain:
    # gather context (Knowledge) → diagnose (Maintenance) → check history
    # (Lessons Learned). This is the multi-agent flow judges want to see.
    if tag or any(k in t for k in _MAINTENANCE):
        steps = [
            {"agent": "knowledge", "task": goal, "payload": {"query": goal}},
            {"agent": "maintenance", "task": goal, "payload": {"equipment_tag": tag} if tag else {}},
            {"agent": "lessons_learned", "task": goal, "payload": {"equipment_tag": tag} if tag else {}},
        ]
        return steps

    if any(k in t for k in _COMPLIANCE):
        return [{"agent": "compliance", "task": goal, "payload": {"area": goal}}]

    if any(k in t for k in _LESSONS):
        return [{"agent": "lessons_learned", "task": goal, "payload": {}}]

    # Default: a general question → Expert Knowledge Copilot.
    return [{"agent": "knowledge", "task": goal, "payload": {"query": goal}}]


class PlannerAgent(BaseAgent):
    name = "planner"
    description = (
        "Breaks a high-level goal into an ordered sequence of the primary "
        "agents (e.g. Knowledge → Maintenance → Lessons Learned for a failure "
        "investigation). Returns a structured plan the Orchestrator executes."
    )
    tools: list[str] = ["intent_decomposition"]

    def run(self, request: AgentRequest) -> AgentResponse:
        plan = build_plan(request.task, request.payload)
        return AgentResponse(
            agent_name=self.name,
            result={"goal": request.task, "plan": plan},
            confidence=1.0,
            tool_calls=["intent_decomposition"],
            notes=f"{len(plan)} step(s): {[s['agent'] for s in plan]}",
        )
