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

from agents.base import AgentRequest, AgentResponse, BaseAgent
from agents.reasoning_agent import Passage, reason_via
from knowledge.store import knowledge_graph, vector_store


class KnowledgeAgent(BaseAgent):
    name = "knowledge"
    description = (
        "Expert Knowledge Copilot -- RAG-powered Q&A over the ingested "
        "document corpus with source citations, confidence scores, and "
        "links to originating documents."
    )
    tools: list[str] = ["chromadb_search", "knowledge_graph_query"]

    def run(self, request: AgentRequest) -> AgentResponse:
        query = request.payload.get("query") or request.task
        top_k = request.payload.get("top_k", 3)

        results = vector_store.search(query, top_k=top_k)
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
