"""
KnowledgeAgent -- "Expert Knowledge Copilot"
(PS8: AI for Industrial Knowledge Intelligence)

RAG-style Q&A over whatever IngestionAgent has ingested into the shared
vector store + knowledge graph. Returns source citations (doc + page) and
a confidence score derived from retrieval similarity -- both are named
PS8 evaluation criteria.

REAL implementation: retrieval (vector search) + answer synthesis via
ReasoningAgent's `synthesize()`. Synthesis uses an LLM when one is
configured (EDGEAI_LLM=openai|ollama) and otherwise falls back to
deterministic offline synthesis -- so the copilot returns a composed,
cited answer in every environment, not a single verbatim passage.
"""

import re

from agents.base import AgentRequest, AgentResponse, BaseAgent
from agents.reasoning_agent import Passage, reason_via
from knowledge.store import knowledge_graph, vector_store

_TAG = re.compile(r"\b[A-Z]{1,3}-\d{2,4}[A-Z]?\b")


class KnowledgeAgent(BaseAgent):
    name = "knowledge"
    description = (
        "Expert Knowledge Copilot -- RAG-powered Q&A over the ingested "
        "document corpus with source citations, confidence scores, and "
        "links to originating documents."
    )
    tools: list[str] = ["hybrid_search", "knowledge_graph_query"]

    def _expand_query(self, query: str) -> str:
        """Graph-augmented retrieval: if the query names an equipment tag, pull
        its related entities (parameters, dates, regulations) from the knowledge
        graph and append them, so retrieval surfaces connected facts the raw
        query wouldn't match lexically."""
        extra: list[str] = []
        for tag in set(_TAG.findall(query or "")):
            for node in knowledge_graph.find_entities(entity_type="equipment_tag", value_contains=tag):
                for rel in knowledge_graph.related_entities(node["id"])[:8]:
                    extra.append(str(rel.get("value", "")))
        return (query + " " + " ".join(extra)).strip() if extra else query

    def run(self, request: AgentRequest) -> AgentResponse:
        query = request.payload.get("query") or request.task
        top_k = request.payload.get("top_k", 3)

        results = vector_store.search(self._expand_query(query), top_k=top_k)
        if not results:
            return AgentResponse(
                agent_name=self.name,
                result="No matching content found -- has anything been ingested yet?",
                confidence=0.0,
                notes="Vector store returned zero results.",
            )

        passages = [
            Passage(text=r.text, source_doc=r.source_doc, page=r.page, similarity=r.similarity)
            for r in results
        ]
        # Synthesis goes through the Orchestrator (ReasoningAgent) when running
        # under it; falls back to local synthesis when unit-tested in isolation.
        synth = reason_via(request.services, query, passages)

        return AgentResponse(
            agent_name=self.name,
            result=synth["answer"],
            confidence=synth["confidence"],
            tool_calls=["chromadb_search", f"{synth['mode']}_synthesis"],
            notes=f"synthesis_mode={synth['mode']}; citations={synth['citations']}",
        )
