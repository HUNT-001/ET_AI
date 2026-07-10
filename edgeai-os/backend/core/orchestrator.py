"""
AI Orchestrator — the center of the platform per Architecture.md.
Responsibilities: request routing, agent scheduling, context management,
memory management. Model selection and tool invocation happen inside agents;
the orchestrator just decides *which* agent(s) to call and in what order.
"""

from __future__ import annotations

from agents import REGISTRY, AGENTS_BY_NAME, AgentRequest, AgentResponse
from backend.core.memory import MemoryLayer


class Orchestrator:
    def __init__(self, memory: MemoryLayer | None = None) -> None:
        self.memory = memory or MemoryLayer()

    def list_agents(self) -> list[dict[str, str]]:
        return [{"name": a.name, "description": a.description} for a in REGISTRY]

    def route(self, task: str) -> list[str]:
        """Very simple routing: return names of agents that claim relevance.
        Replace with embedding-based routing or an explicit planning agent call
        once PlannerAgent has real logic."""
        matches = [a.name for a in REGISTRY if a.can_handle(task)]
        return matches or ["reasoning"]  # fall back to general reasoning

    def dispatch(self, agent_name: str, task: str, payload: dict | None = None) -> AgentResponse:
        agent = AGENTS_BY_NAME.get(agent_name)
        if agent is None:
            raise KeyError(f"No such agent: {agent_name}. Known: {list(AGENTS_BY_NAME)}")

        request = AgentRequest(
            task=task,
            payload=payload or {},
            context={"recent": self.memory.recent()},
        )
        response = agent.run(request)

        self.memory.append_short_term(
            {"agent": agent_name, "task": task, "result": str(response.result)}
        )
        return response

    def handle(self, task: str, payload: dict | None = None) -> list[AgentResponse]:
        """Top-level entry point: route + dispatch to every matching agent."""
        agent_names = self.route(task)
        return [self.dispatch(name, task, payload) for name in agent_names]
