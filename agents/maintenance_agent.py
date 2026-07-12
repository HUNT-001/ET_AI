"""
MaintenanceAgent — "Maintenance Intelligence & RCA Agent"
(PS8: AI for Industrial Knowledge Intelligence)

Fuses work order history, equipment failure records, OEM manuals, inspection
findings, and real-time operating conditions to generate predictive
maintenance recommendations, Root Cause Analysis (RCA) support, and
optimised maintenance schedules.

REAL implementation (not a stub). Pipeline for a given equipment tag:
  1. Locate the equipment node in the knowledge graph and pull its
     cross-document context (which docs mention it, related entities).
  2. Retrieve the equipment's maintenance/inspection passages from the
     vector store (RAG).
  3. Score degradation/failure risk via ForecastingAgent over those passages.
  4. Synthesize an RCA narrative (grounded + cited) via KnowledgeAgent's
     shared reasoning.
  5. Emit a recommended action, priority, and the evidence behind it.
"""

from __future__ import annotations

import re

from agents.base import AgentRequest, AgentResponse, BaseAgent
from agents.forecasting_agent import score_degradation
from agents.monitoring_agent import detect_anomalies
from agents.reasoning_agent import Passage, reason_via
from knowledge.store import knowledge_graph, vector_store

_TAG = re.compile(r"\b[A-Z]{1,3}-\d{2,4}[A-Z]?\b")


def _priority_for(level: str) -> str:
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(level, "Medium")


class MaintenanceAgent(BaseAgent):
    name = "maintenance"
    description = (
        "Maintenance Intelligence & RCA Agent — fuses work order history, "
        "equipment failure records, OEM manuals, inspection findings, and "
        "real-time conditions to generate predictive maintenance "
        "recommendations, RCA support, and optimised maintenance schedules."
    )
    tools: list[str] = ["forecasting_model", "knowledge_graph_query", "rca_reasoner"]

    def _resolve_tag(self, request: AgentRequest) -> str | None:
        tag = request.payload.get("equipment_tag")
        if tag:
            return tag
        m = _TAG.search(request.payload.get("query") or request.task or "")
        return m.group(0) if m else None

    def run(self, request: AgentRequest) -> AgentResponse:
        tag = self._resolve_tag(request)
        if not tag:
            return AgentResponse(
                agent_name=self.name,
                result=None,
                confidence=0.0,
                notes="No equipment tag provided or found. Pass payload={'equipment_tag': 'P-101A'}.",
            )

        # 1. Knowledge-graph context for this asset.
        nodes = knowledge_graph.find_entities(entity_type="equipment_tag", value_contains=tag)
        graph_context = {}
        if nodes:
            node = nodes[0]
            related = knowledge_graph.related_entities(node["id"])
            graph_context = {
                "node": node["value"],
                "source_docs": node["source_docs"],
                "related_entities": [
                    {"type": r["entity_type"], "value": r["value"]} for r in related
                ],
            }

        # 2. Retrieve the asset's maintenance/inspection passages.
        results = vector_store.search(f"{tag} maintenance inspection failure vibration", top_k=5)
        if not results:
            return AgentResponse(
                agent_name=self.name,
                result={"equipment_tag": tag, "note": "No source documents mention this asset yet."},
                confidence=0.0,
                notes="Nothing ingested for this equipment tag.",
            )

        fused_text = " ".join(r.text for r in results)
        services = request.services

        # 3. Failure/degradation risk — via ForecastingAgent (through the
        # orchestrator when available, local fallback otherwise).
        risk = self._forecast(services, tag, fused_text)

        # 3b. Live-condition anomaly — via MonitoringAgent. Fused into the
        # risk if the caller supplied sensor readings; degrades gracefully
        # (no readings → no live signal, risk unchanged).
        readings = request.payload.get("readings", [])
        monitor = self._monitor(services, tag, readings)
        if monitor.get("anomaly"):
            bump = round(0.15 * monitor.get("score", 0.0), 3)
            risk["risk"] = round(min(1.0, risk["risk"] + bump), 3)
            risk["level"] = "high" if risk["risk"] >= 0.6 else "medium" if risk["risk"] >= 0.3 else "low"
            risk["factors"].append(f"Live-condition anomaly detected (score {monitor['score']}) [+{bump}]")

        # 4. RCA narrative — grounded + cited, via ReasoningAgent.
        passages = [
            Passage(text=r.text, source_doc=r.source_doc, page=r.page, similarity=r.similarity)
            for r in results
        ]
        rca = reason_via(
            services,
            f"What is the root cause of the issues reported on {tag}, and what maintenance action is recommended?",
            passages,
        )

        # 5. Recommendation.
        priority = _priority_for(risk["level"])
        recommendation = (
            f"{tag}: {risk['level'].upper()} degradation risk (score {risk['risk']}). "
            f"Recommended priority: {priority}."
        )

        # 6. Persist to shared memory: high-risk findings go to the incident
        # archive (LessonsLearnedAgent reads it) and every recommendation is
        # committed to long-term memory for traceability.
        if services is not None and services.memory is not None:
            if risk["level"] in {"high", "medium"}:
                services.memory.log_incident({
                    "equipment_tag": tag,
                    "risk": risk["risk"],
                    "level": risk["level"],
                    "factors": risk["factors"],
                    "source_docs": graph_context.get("source_docs", []),
                })
            services.memory.commit_long_term({"type": "maintenance_recommendation",
                                              "equipment_tag": tag, "recommendation": recommendation})

        result = {
            "equipment_tag": tag,
            "risk": risk,
            "monitoring": monitor,
            "recommendation": recommendation,
            "priority": priority,
            "rca_narrative": rca["answer"],
            "citations": rca["citations"],
            "graph_context": graph_context,
        }

        return AgentResponse(
            agent_name=self.name,
            result=result,
            confidence=risk["risk"],
            tool_calls=["knowledge_graph_query", "chromadb_search", "forecasting", "monitoring", f"{rca['mode']}_synthesis"],
            notes=f"RCA for {tag}; risk={risk['level']}; synthesis={rca['mode']}",
        )

    # ---- sub-agent calls (orchestrator path, with local fallback) ----
    @staticmethod
    def _forecast(services, tag: str, fused_text: str) -> dict:
        if services is not None:
            resp = services.invoke("forecasting", tag, {"context_text": fused_text})
            if isinstance(resp.result, dict):
                return dict(resp.result)
        return score_degradation(fused_text)

    @staticmethod
    def _monitor(services, tag: str, readings: list) -> dict:
        if services is not None:
            resp = services.invoke("monitoring", tag, {"readings": readings})
            if isinstance(resp.result, dict):
                return resp.result
        return detect_anomalies(readings)
