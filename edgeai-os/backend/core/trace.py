"""
Lightweight execution tracing (observability) — records a span per agent
dispatch so every request has an auditable trail: which agents ran, how long
they took, their confidence, and which tools they called.

Deliberately dependency-free (no OpenTelemetry/Langfuse required) so it stays
fully local and always on. The same span data can be exported to OTel/Langfuse
later without changing call sites.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from threading import Lock


@dataclass
class Span:
    agent: str
    task: str
    ms: float
    confidence: float | None
    tools: list = field(default_factory=list)
    ts: float = 0.0


class Tracer:
    def __init__(self, cap: int = 500):
        self._spans: list[Span] = []
        self._cap = cap
        self._lock = Lock()

    def record(self, agent: str, task: str, ms: float, confidence, tools) -> None:
        with self._lock:
            self._spans.append(Span(agent, (task or "")[:200], round(ms, 2),
                                    confidence, list(tools or []), time.time()))
            if len(self._spans) > self._cap:
                self._spans.pop(0)

    def recent(self, n: int = 50) -> list[dict]:
        with self._lock:
            return [asdict(s) for s in self._spans[-n:]]

    def summary(self) -> dict:
        """Per-agent aggregates — the numbers an observability dashboard shows."""
        with self._lock:
            agg: dict[str, dict] = {}
            for s in self._spans:
                a = agg.setdefault(s.agent, {"calls": 0, "total_ms": 0.0})
                a["calls"] += 1
                a["total_ms"] += s.ms
            for a in agg.values():
                a["avg_ms"] = round(a["total_ms"] / a["calls"], 2) if a["calls"] else 0.0
                a["total_ms"] = round(a["total_ms"], 2)
            return {"total_spans": len(self._spans), "by_agent": agg}


# Process-wide tracer.
tracer = Tracer()
