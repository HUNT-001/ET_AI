"""
AI Orchestrator — the center of the platform per Architecture.md.
Responsibilities: request routing, agent scheduling, task planning, context
management, memory management. Model selection and tool invocation happen
inside agents; the orchestrator decides *which* agent(s) run and in what order,
and is the single conduit through which agents call one another.
"""

from __future__ import annotations

import os
import re
import time

from agents import REGISTRY, AGENTS_BY_NAME, AgentRequest, AgentResponse, AgentServices
from backend.core.memory import MemoryLayer
from backend.core.trace import tracer

_EQUIPMENT_TAG = re.compile(r"\b[A-Z]{1,3}-\d{2,4}[A-Z]?\b")

# Intent → trigger keywords. Ordered specificity: the most domain-specific
# intents (compliance, maintenance, lessons) are scored before the general
# knowledge fallback. This replaces the old name-substring matching, which
# only fired when a task literally contained an agent's name.
_INTENTS: list[tuple[str, list[str]]] = [
    ("ingestion", ["ingest", "upload", "load document", "add document", "index this"]),
    ("compliance", ["complian", "regulat", "audit", "oisd", "peso", "factory act",
                     "gap", "non-conform", "nonconform", "deviation", "evidence package"]),
    ("maintenance", ["maintenance", "rca", "root cause", "root-cause", "failure", "failed",
                      "repair", "vibration", "bearing", "degradation", "breakdown", "fault"]),
    ("lessons_learned", ["lesson", "recurring", "recurrence", "pattern", "seen before",
                          "near-miss", "near miss", "systemic", "happened again",
                          "before", "happened before", "ever seen"]),
]


class Orchestrator:
    def __init__(self, memory: MemoryLayer | None = None) -> None:
        self.memory = memory or MemoryLayer()

    # ---- registry / introspection ----
    def list_agents(self) -> list[dict[str, str]]:
        return [{"name": a.name, "description": a.description} for a in REGISTRY]

    # ---- services injected into every agent ----
    def _services(self) -> AgentServices:
        """The handle agents use to call other agents and reach shared memory."""
        return AgentServices(invoke=self.dispatch, memory=self.memory)

    # ---- routing ----
    def classify(self, task: str) -> str:
        """Intent classification → the single best-fit primary agent.
        General questions (and anything with no domain signal) go to the
        Expert Knowledge Copilot."""
        t = (task or "").lower()
        scores: dict[str, int] = {}
        for agent, keywords in _INTENTS:
            scores[agent] = sum(1 for k in keywords if k in t)
        # An equipment tag in the task strongly implies a maintenance/RCA intent.
        if _EQUIPMENT_TAG.search(task or ""):
            scores["maintenance"] = scores.get("maintenance", 0) + 1
        best = max(scores, key=scores.get) if scores else "knowledge"
        return best if scores.get(best, 0) > 0 else "knowledge"

    def route(self, task: str) -> list[str]:
        """Return the agent(s) that should handle a task. Single best intent by
        default; PlannerAgent (via plan_and_execute) handles multi-step goals."""
        return [self.classify(task)]

    # ---- dispatch (also serves as the agents' invoke() conduit) ----
    def dispatch(self, agent_name: str, task: str, payload: dict | None = None) -> AgentResponse:
        agent = AGENTS_BY_NAME.get(agent_name)
        if agent is None:
            raise KeyError(f"No such agent: {agent_name}. Known: {list(AGENTS_BY_NAME)}")

        request = AgentRequest(
            task=task,
            payload=payload or {},
            context={"recent": self.memory.recent()},
            services=self._services(),
        )
        t0 = time.perf_counter()
        response = agent.run(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Observability: record a span for every dispatch (also covers nested
        # agent-to-agent calls, since those route back through dispatch).
        tracer.record(agent_name, task, elapsed_ms, response.confidence, response.tool_calls)
        self.memory.append_short_term(
            {"agent": agent_name, "task": task, "result": str(response.result)[:500]}
        )
        return response

    def handle(self, task: str, payload: dict | None = None) -> list[AgentResponse]:
        """Top-level entry point: route to the best agent and dispatch."""
        return [self.dispatch(name, task, payload) for name in self.route(task)]

    # ---- planning: decompose a goal and execute the plan ----
    def plan_and_execute(self, goal: str, payload: dict | None = None) -> dict:
        """Ask PlannerAgent for an ordered plan, then execute each step,
        threading results through shared memory. This is the multi-agent flow
        from Architecture.md (e.g. Knowledge → Maintenance → Lessons Learned).

        Opt into the LangGraph runtime with EDGEAI_RUNTIME=langgraph; the native
        path below stays the default and the automatic fallback."""
        if os.environ.get("EDGEAI_RUNTIME", "").lower() == "langgraph":
            try:
                from backend.core.langgraph_runtime import run_graph
                return run_graph(goal, self, payload)
            except Exception as e:
                print(f"[orchestrator] LangGraph runtime unavailable ({e}); using native runtime.")

        plan_resp = self.dispatch("planner", goal, payload)
        plan = (plan_resp.result or {}).get("plan", []) if isinstance(plan_resp.result, dict) else []

        results: list[dict] = []
        for step in plan:
            r = self.dispatch(
                step["agent"],
                step.get("task", goal),
                {**(payload or {}), **step.get("payload", {})},
            )
            results.append({
                "agent": r.agent_name,
                "confidence": r.confidence,
                "result": r.result,
                "notes": r.notes,
            })
        self.memory.commit_long_term({"goal": goal, "plan": plan})
        return {"goal": goal, "plan": plan, "results": results}
