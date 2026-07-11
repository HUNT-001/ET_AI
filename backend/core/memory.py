"""
Shared Memory Layer — per Architecture.md:
Working -> Short-term -> Long-term -> Knowledge Graph -> Vector DB -> Historical -> Incident Archive

This is an in-memory stub so the Orchestrator is testable today. Swap each
method's internals for Redis (working/short-term), Postgres (long-term/
historical/incident archive), Neo4j (knowledge graph), and Chroma/Qdrant
(vector DB) without changing the interface agents/orchestrator rely on.
"""

from __future__ import annotations

from typing import Any


class MemoryLayer:
    def __init__(self) -> None:
        self._working: dict[str, Any] = {}
        self._short_term: list[dict[str, Any]] = []
        self._long_term: list[dict[str, Any]] = []
        self._incident_archive: list[dict[str, Any]] = []

    # --- working memory: current task/session scratch space ---
    def set_working(self, key: str, value: Any) -> None:
        self._working[key] = value

    def get_working(self, key: str, default: Any = None) -> Any:
        return self._working.get(key, default)

    # --- short-term: recent turns/events, capped ring buffer ---
    def append_short_term(self, event: dict[str, Any], cap: int = 200) -> None:
        self._short_term.append(event)
        if len(self._short_term) > cap:
            self._short_term.pop(0)

    def recent(self, n: int = 10) -> list[dict[str, Any]]:
        return self._short_term[-n:]

    # --- long-term: durable facts/decisions worth keeping ---
    def commit_long_term(self, record: dict[str, Any]) -> None:
        self._long_term.append(record)

    # --- incident archive: safety/compliance-relevant events ---
    def log_incident(self, incident: dict[str, Any]) -> None:
        self._incident_archive.append(incident)

    def snapshot(self) -> dict[str, Any]:
        """Full dump — useful for debugging and for the /memory API route."""
        return {
            "working": self._working,
            "short_term": self._short_term,
            "long_term": self._long_term,
            "incident_archive": self._incident_archive,
        }
