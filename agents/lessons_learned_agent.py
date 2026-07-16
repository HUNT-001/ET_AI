"""
LessonsLearnedAgent — "Lessons Learned & Failure Intelligence Engine"
(PS8: AI for Industrial Knowledge Intelligence)

Analyses incident reports, near-miss records, audit findings, and quality
non-conformances across the organisation's history to identify systemic
patterns invisible to any individual review, and proactively pushes
relevant warnings to operational teams before similar conditions recur.

This is the platform's answer to the "knowledge cliff" problem in the PS8
brief: undocumented tribal knowledge from retiring engineers should surface
here as a pattern, not disappear.

REAL implementation (not a stub). Pipeline:
  1. Find equipment that appears across multiple documents (cross-document
     linkage in the knowledge graph) OR whose passages contain recurrence /
     repeat-failure language — the signal of a systemic, not one-off, issue.
  2. For each such asset, assemble the evidence (which documents, what
     recurring symptom) into a pattern.
  3. Rank patterns by strength and hand the strongest to NotificationAgent
     as a proactive, severity-tagged warning.
"""

from __future__ import annotations

import os
import re

from agents.base import AgentRequest, AgentResponse, BaseAgent
from agents.notification_agent import build_notification
from knowledge.store import knowledge_graph, vector_store

_RECURRENCE_LANG = re.compile(
    r"recurr\w+|similar\s+\w*\s*anomaly|again|repeat\w*|prior\s+(?:related\s+)?incident|seen\s+before",
    re.I,
)


def _mine_patterns() -> list[dict]:
    """Return recurring-failure patterns found across the ingested corpus."""
    patterns: list[dict] = []

    # Signal A: equipment tags linked across >1 document (cross-doc linkage).
    for ent in knowledge_graph.cross_document_entities():
        if ent["entity_type"] != "equipment_tag":
            continue
        patterns.append({
            "equipment_tag": ent["value"],
            "signal": "cross_document_recurrence",
            "evidence": [os.path.basename(d) for d in ent["source_docs"]],
            "strength": min(1.0, 0.4 + 0.2 * len(ent["source_docs"])),
        })

    known = {p["equipment_tag"] for p in patterns}

    # Signal B: recurrence language in an asset's passages (even single-doc).
    for ent in knowledge_graph.find_entities(entity_type="equipment_tag"):
        tag = ent["value"]
        if tag in known:
            continue
        hits = vector_store.search(f"{tag} recurrence repeat prior incident anomaly", top_k=3)
        recurrence_docs = []
        for r in hits:
            # Require the tag itself to appear in the same passage as the
            # recurrence language — avoids flagging every asset that merely
            # shares a document with an unrelated recurring issue.
            if _RECURRENCE_LANG.search(r.text) and tag in r.text:
                recurrence_docs.append(f"{os.path.basename(r.source_doc)} p.{r.page}")
        recurrence_docs = sorted(set(recurrence_docs))  # dedupe repeated doc/page hits
        if recurrence_docs:
            patterns.append({
                "equipment_tag": tag,
                "signal": "recurrence_language",
                "evidence": recurrence_docs,
                "strength": min(1.0, 0.3 + 0.15 * len(recurrence_docs)),
            })

    patterns.sort(key=lambda p: p["strength"], reverse=True)
    return patterns


def _merge_memory_incidents(patterns: list[dict], services) -> list[dict]:
    """Boost/introduce patterns for assets that have logged incidents in the
    shared MemoryLayer's incident archive."""
    if services is None or getattr(services, "memory", None) is None:
        return patterns
    archive = services.memory.snapshot().get("incident_archive", [])
    by_tag: dict[str, int] = {}
    for inc in archive:
        tag = inc.get("equipment_tag")
        if tag:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    index = {p["equipment_tag"]: p for p in patterns}
    for tag, count in by_tag.items():
        if tag in index:
            index[tag]["strength"] = min(1.0, index[tag]["strength"] + 0.1 * count)
            index[tag]["signal"] = index[tag]["signal"] + "+logged_incident"
        else:
            patterns.append({
                "equipment_tag": tag,
                "signal": "logged_incident",
                "evidence": [f"{count} incident record(s) in shared memory"],
                "strength": min(1.0, 0.4 + 0.1 * count),
            })
    patterns.sort(key=lambda p: p["strength"], reverse=True)
    return patterns


class LessonsLearnedAgent(BaseAgent):
    name = "lessons_learned"
    description = (
        "Lessons Learned & Failure Intelligence Engine — analyses incident "
        "reports, near-miss records, audit findings, and quality "
        "non-conformances to identify systemic patterns and proactively "
        "push warnings to operational teams before similar conditions recur."
    )
    tools: list[str] = ["pattern_mining", "knowledge_graph_query", "notification_dispatch"]

    def run(self, request: AgentRequest) -> AgentResponse:
        patterns = _mine_patterns()

        # Fold in incidents logged to shared memory by MaintenanceAgent. This
        # closes the loop: a high-risk finding recorded during a maintenance
        # investigation resurfaces here as a corroborated pattern signal.
        patterns = _merge_memory_incidents(patterns, request.services)

        # Optionally focus on a specific asset if the caller named one.
        focus = request.payload.get("equipment_tag")
        if focus:
            patterns = [p for p in patterns if focus.lower() in p["equipment_tag"].lower()]

        notifications = []
        for p in patterns:
            severity = "high" if p["strength"] >= 0.6 else "medium" if p["strength"] >= 0.4 else "low"
            note = build_notification(
                title=f"Recurring failure pattern: {p['equipment_tag']}",
                message=(
                    f"{p['equipment_tag']} shows a {p['signal'].replace('_', ' ')} pattern across "
                    f"{len(p['evidence'])} record(s): {', '.join(p['evidence'])}. "
                    f"Review before the next similar condition recurs."
                ),
                severity=severity,
            )
            notifications.append(note)

        result = {
            "patterns_found": len(patterns),
            "patterns": patterns,
            "notifications": notifications,
        }
        confidence = round(max((p["strength"] for p in patterns), default=0.0), 3)
        summary = (
            f"{len(patterns)} recurring-failure pattern(s) surfaced; "
            f"{len(notifications)} proactive warning(s) queued."
            if patterns else "No recurring failure patterns found in the current corpus."
        )

        return AgentResponse(
            agent_name=self.name,
            result=result,
            confidence=confidence,
            tool_calls=["pattern_mining", "knowledge_graph_query", "severity_router"],
            notes=summary,
        )
