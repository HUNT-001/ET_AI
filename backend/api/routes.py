import os
import tempfile
import time

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from agents.reasoning_agent import Passage, reason_via
from agents.verifier_agent import verify_answer
from backend.core.orchestrator import Orchestrator
from knowledge.pipeline import ingest_pdf
from knowledge.store import knowledge_graph, vector_store

router = APIRouter()
orchestrator = Orchestrator()

_SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__), "..", "..", "datasets", "samples", "sample_maintenance_report.pdf"
)
# Assumed manual-search baseline (minutes) — the "before" side of the
# time-to-answer comparison the dashboard renders. Conservative vs. the PS8
# brief's framing of hours lost to cross-system searching.
_MANUAL_SEARCH_BASELINE_MS = 8 * 60 * 1000


class TaskRequest(BaseModel):
    task: str
    payload: dict = {}


class DispatchRequest(BaseModel):
    agent: str
    task: str
    payload: dict = {}


class AskRequest(BaseModel):
    query: str
    top_k: int = 3


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/agents")
def list_agents():
    return orchestrator.list_agents()


@router.get("/agents/primary")
def list_primary_agents():
    """The 5 agents named explicitly in the PS8 brief's 'What You May Build'."""
    from agents import PRIMARY_AGENTS
    return [{"name": a.name, "description": a.description} for a in PRIMARY_AGENTS]


@router.post("/orchestrate")
def orchestrate(req: TaskRequest):
    """Route a task to the best-fit agent (intent classification) and return
    the response(s)."""
    responses = orchestrator.handle(req.task, req.payload)
    return [r.__dict__ for r in responses]


@router.post("/plan")
def plan(req: TaskRequest):
    """Decompose a high-level goal into a multi-agent plan and execute it
    (PlannerAgent → ordered agent calls). Returns the plan and each step's
    result."""
    return orchestrator.plan_and_execute(req.task, req.payload)


@router.get("/route")
def route(task: str):
    """Introspection: show which agent a task would be routed to and why."""
    return {"task": task, "routed_to": orchestrator.classify(task)}


@router.post("/agents/dispatch")
def dispatch(req: DispatchRequest):
    """Call one specific agent directly, bypassing routing."""
    try:
        response = orchestrator.dispatch(req.agent, req.task, req.payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return response.__dict__


@router.get("/memory")
def memory_snapshot():
    return orchestrator.memory.snapshot()


@router.post("/ask")
def ask(req: AskRequest):
    """Expert Knowledge Copilot endpoint for the dashboard: retrieve, synthesize
    a cited answer, and report both which agent the query routed to and the
    time-to-answer vs. a manual-search baseline (the headline demo metric)."""
    t0 = time.perf_counter()
    results = vector_store.search(req.query, top_k=req.top_k)
    passages = [Passage(r.text, r.source_doc, r.page, r.similarity) for r in results]
    synth = reason_via(None, req.query, passages)
    # Supervisor pass: verify grounding before returning to the technician.
    verification = verify_answer(synth["answer"], passages)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "query": req.query,
        "routed_to": orchestrator.classify(req.query),
        "answer": synth["answer"],
        "citations": synth["citations"],
        "confidence": synth["confidence"],
        "mode": synth["mode"],
        "verification": verification,
        "elapsed_ms": elapsed_ms,
        "manual_baseline_ms": _MANUAL_SEARCH_BASELINE_MS,
    }


@router.get("/knowledge/stats")
def knowledge_stats():
    """Knowledge-layer status for the dashboard: graph size, cross-document
    linkage, documents ingested, and vector count."""
    stats = knowledge_graph.stats()
    docs = sorted({d for e in knowledge_graph.all_entities() for d in e["source_docs"]})
    try:
        vector_count = vector_store.collection.count()
    except Exception:
        vector_count = None
    return {
        **stats,
        "documents_ingested": len(docs),
        "documents": [os.path.basename(d) for d in docs],
        "vector_chunks": vector_count,
        "ready": stats["total_entities"] > 0,
    }


@router.post("/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)):
    """Upload a document (PDF) from the dashboard and ingest it into the shared
    knowledge graph + vector store. Scanned PDFs are OCR'd if Tesseract is
    installed; otherwise a clear 422 is returned."""
    data = await file.read()
    safe_name = os.path.basename(file.filename or "upload.pdf")
    tmp_path = os.path.join(tempfile.gettempdir(), safe_name)
    with open(tmp_path, "wb") as f:
        f.write(data)
    try:
        result = ingest_pdf(tmp_path, graph=knowledge_graph, vector_store=vector_store)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    return {
        "source_doc": safe_name,
        "pages_ingested": result.num_pages,
        "chunks_created": result.num_chunks,
        "entities_found": result.entities_found,
    }


@router.post("/ingest/sample")
def ingest_sample():
    """One-click ingest of the bundled sample maintenance report so the
    dashboard is demoable with zero setup."""
    path = os.path.abspath(_SAMPLE_PDF)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Sample not found at {path}")
    result = ingest_pdf(path, graph=knowledge_graph, vector_store=vector_store)
    return {
        "source_doc": os.path.basename(result.source_doc),
        "pages_ingested": result.num_pages,
        "chunks_created": result.num_chunks,
        "entities_found": result.entities_found,
    }
