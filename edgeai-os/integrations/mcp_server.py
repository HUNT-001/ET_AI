"""
EdgeAI-OS as an MCP server.

This exposes the industrial knowledge platform over the Model Context Protocol,
so any MCP client — Claude Desktop, an IDE, another agent — can query the plant
brain directly: ask cited questions, pull equipment risk, check compliance,
and ingest documents. The whole thing still runs locally (privacy-first): the
MCP client talks to this local server, which uses local retrieval + (optionally)
local Ollama inference. Nothing leaves the host.

The tool logic is factored into `*_impl` functions so it is unit-testable
without the MCP runtime. `mcp.run()` wires them to stdio for the client.

Run (after `pip install "mcp[cli]"`):
    python integrations/mcp_server.py

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "edgeai-os": {
          "command": "python",
          "args": ["D:/ET_AI/edgeai-os/integrations/mcp_server.py"],
          "env": {"EDGEAI_LLM": "ollama", "EDGEAI_OLLAMA_MODEL": "qwen2.5-rag", "EDGEAI_EMBED": "ollama"}
        }
      }
    }
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import AgentRequest
from agents.reasoning_agent import Passage, reason_via
from agents.verifier_agent import verify_answer
from backend.core.orchestrator import Orchestrator
from knowledge.pipeline import ingest_pdf
from knowledge.store import knowledge_graph, vector_store

_orch = Orchestrator()
_SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                       "sample_maintenance_report.pdf")


# ---------------------------------------------------------------- tool logic
def ask_knowledge_impl(query: str, top_k: int = 3) -> dict:
    """Answer an industrial question with source citations and a grounding check."""
    results = vector_store.search(query, top_k=top_k)
    passages = [Passage(r.text, r.source_doc, r.page, r.similarity) for r in results]
    synth = reason_via(None, query, passages)
    verification = verify_answer(synth["answer"], passages)
    return {
        "answer": synth["answer"],
        "citations": synth["citations"],
        "confidence": synth["confidence"],
        "verification": {"status": verification["status"], "coverage": verification["coverage"],
                         "flagged": verification["flagged"]},
        "synthesis_mode": synth["mode"],
    }


def equipment_risk_impl(equipment_tag: str) -> dict:
    """Root-cause analysis + degradation risk for an equipment tag."""
    resp = _orch.dispatch("maintenance", equipment_tag, {"equipment_tag": equipment_tag})
    return resp.result


def check_compliance_impl(area: str) -> dict:
    """Regulatory coverage gaps + recorded deviations for an area/unit."""
    resp = _orch.dispatch("compliance", area, {"area": area})
    return resp.result


def failure_patterns_impl() -> dict:
    """Recurring failure patterns surfaced across the corpus."""
    resp = _orch.dispatch("lessons_learned", "patterns", {})
    return resp.result


def ingest_document_impl(path: str) -> dict:
    """Ingest a PDF into the shared knowledge graph + vector index."""
    result = ingest_pdf(path, graph=knowledge_graph, vector_store=vector_store)
    return {"source_doc": os.path.basename(result.source_doc), "pages": result.num_pages,
            "chunks": result.num_chunks, "entities_found": result.entities_found}


def graph_stats_impl() -> dict:
    """Knowledge-graph size + cross-document linkage stats."""
    return knowledge_graph.stats()


# ---------------------------------------------------------------- MCP wiring
def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("EdgeAI-OS")
    mcp.tool()(ask_knowledge_impl)
    mcp.tool()(equipment_risk_impl)
    mcp.tool()(check_compliance_impl)
    mcp.tool()(failure_patterns_impl)
    mcp.tool()(ingest_document_impl)
    mcp.tool()(graph_stats_impl)
    return mcp


if __name__ == "__main__":
    # Auto-ingest the bundled sample so the server answers immediately in a demo.
    try:
        if knowledge_graph.stats().get("total_entities", 0) == 0 and os.path.exists(_SAMPLE):
            ingest_document_impl(os.path.abspath(_SAMPLE))
    except Exception as e:
        print(f"[mcp_server] sample ingest skipped: {e}", file=sys.stderr)
    build_server().run()
