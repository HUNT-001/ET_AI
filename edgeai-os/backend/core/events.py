"""
Minimal in-process event bus for event-driven workflows.

Rather than manually orchestrating "after ingest, also re-check compliance and
refresh lessons," components publish events and subscribers react. This makes
the platform reactive: ingest a document and the compliance + lessons views
update automatically, no explicit call chain.

In-process and synchronous for the demo (deterministic, easy to trace); the
same publish/subscribe interface maps onto Redis/Kafka later without changing
publishers.
"""

from __future__ import annotations

from typing import Callable


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        self._subs.setdefault(event, []).append(handler)

    def publish(self, event: str, payload: dict) -> list[dict]:
        reactions: list[dict] = []
        for h in self._subs.get(event, []):
            name = getattr(h, "__name__", str(h))
            try:
                reactions.append({"handler": name, "result": h(payload)})
            except Exception as e:  # a failing subscriber must not break ingest
                reactions.append({"handler": name, "error": str(e)})
        return reactions


bus = EventBus()

# --- default subscribers for document_ingested (lazy imports avoid cycles) ---
_registered = False


def _on_ingest_recheck_compliance(payload: dict) -> dict:
    from agents.compliance_agent import ComplianceAgent
    from agents.base import AgentRequest

    area = payload.get("area", "plant")
    r = ComplianceAgent().run(AgentRequest(task="compliance", payload={"area": area}))
    return {"gap_count": r.result.get("gap_count"), "coverage_gaps": r.result.get("coverage_gaps")}


def _on_ingest_refresh_lessons(payload: dict) -> dict:
    from agents.lessons_learned_agent import LessonsLearnedAgent
    from agents.base import AgentRequest

    r = LessonsLearnedAgent().run(AgentRequest(task="lessons_learned", payload={}))
    return {"patterns_found": r.result.get("patterns_found")}


def _on_ingest_build_episodes(payload: dict) -> dict:
    from agents.reasoning_engine import populate_episodes_from_corpus

    return {"episodes_built": populate_episodes_from_corpus()}


def register_default_subscribers() -> None:
    """Idempotently wire the standard document_ingested reactions."""
    global _registered
    if _registered:
        return
    bus.subscribe("document_ingested", _on_ingest_recheck_compliance)
    bus.subscribe("document_ingested", _on_ingest_refresh_lessons)
    bus.subscribe("document_ingested", _on_ingest_build_episodes)
    _registered = True


register_default_subscribers()
