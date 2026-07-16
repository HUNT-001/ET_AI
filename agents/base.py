"""
BaseAgent — the common interface every specialized agent implements.

Design goal (per Architecture.md): each agent is a small, swappable unit with
a clean input -> output contract and an explicit list of tools it may call.
The Orchestrator never needs to know an agent's internals, only this contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentServices:
    """Handle the Orchestrator injects into every AgentRequest so an agent can
    call *other* agents and reach shared memory WITHOUT importing them directly.

    This is what enforces the 'Orchestrator is the center' principle from
    Architecture.md: MaintenanceAgent asks for the ForecastingAgent's output
    via `services.invoke("forecasting", ...)` rather than importing its
    internals, so routing, memory logging, and future cross-cutting concerns
    (tracing, auth, caching) all live in one place.

    `invoke(agent_name, task, payload) -> AgentResponse`
    `memory` is the shared MemoryLayer (or None when an agent is unit-tested
    in isolation, in which case agents fall back to a direct local path).
    """
    invoke: Callable[..., "AgentResponse"]
    memory: Any = None


@dataclass
class AgentRequest:
    """Standard input envelope passed to any agent."""
    task: str
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)  # shared memory slice
    services: "AgentServices | None" = None  # cross-agent + memory access


@dataclass
class AgentResponse:
    """Standard output envelope returned by any agent."""
    agent_name: str
    result: Any
    confidence: float | None = None
    tool_calls: list[str] = field(default_factory=list)
    notes: str | None = None


class BaseAgent(ABC):
    """All agents (Planner, Vision, Reasoning, Compliance, ...) subclass this."""

    name: str = "base_agent"
    description: str = "Override me."
    tools: list[str] = []  # names of tools/models this agent is allowed to call

    @abstractmethod
    def run(self, request: AgentRequest) -> AgentResponse:
        """Execute the agent's task and return a structured response."""
        raise NotImplementedError

    def can_handle(self, task: str) -> bool:
        """Cheap relevance check the Orchestrator uses for routing.
        Override for smarter matching (embeddings, keyword rules, etc.)."""
        return task.lower() in self.name.lower()
