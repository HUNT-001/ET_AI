import os
import tempfile
import time

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from agents.notification_agent import build_notification
from agents.reflection import answer_with_reflection
from agents.reasoning_engine import reason
from agents.simulation import simulate_failure
from backend.core.events import bus
from backend.core.workflow import WorkflowEngine
from backend.core.orchestrator import Orchestrator
from backend.core.policy import approval_decision
from backend.core.trace import tracer
from knowledge.pipeline import ingest_pdf
from knowledge.store import knowledge_graph, vector_store

router = APIRouter()
orchestrator = Orchestrator()

_SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__), "..", "..", "datasets", "samples", "sample_maintenance_report.pdf"
)
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
    from agents import PRIMARY_AGENTS
    return [{"name": a.name, "description": a.description} for a in PRIMARY_AGENTS]


@router.post("/orchestrate")
def orchestrate(req: TaskRequest):
    return [r.__dict__ for r in orchestrator.handle(req.task, req.payload)]


@router.post("/plan")
def plan(req: TaskRequest):
    return orchestrator.plan_and_execute(req.task, req.payload)


@router.get("/route")
def route(task: str):
    return {"task": task, "routed_to": orchestrator.classify(task)}


@router.post("/agents/dispatch")
def dispatch(req: DispatchRequest):
    try:
        response = orchestrator.dispatch(req.agent, req.task, req.payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return response.__dict__


@router.get("/memory")
def memory_snapshot():
    return orchestrator.memory.snapshot()


@router.get("/trace")
def trace():
    """Observability: per-agent execution summary + the recent span trail."""
    return {"summary": tracer.summary(), "recent": tracer.recent(50)}


@router.post("/ask")
def ask(req: AskRequest):
    """Expert Knowledge Copilot: retrieve → synthesize (cited) → verify →
    reflect/retry if ungrounded → human-approval gate. Reports routing, the
    grounding verification, whether it reflected, and time-to-answer."""
    t0 = time.perf_counter()
    out = answer_with_reflection(req.query, vector_store.search, top_k=req.top_k)
    approval = approval_decision(out["confidence"], out["verification"])
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "query": req.query,
        "routed_to": orchestrator.classify(req.query),
        "answer": out["answer"],
        "citations": out["citations"],
        "sources": out["sources"],
        "confidence": out["confidence"],
        "mode": out["mode"],
        "verification": out["verification"],
        "reflected": out["reflected"],
        "approval": approval,
        "elapsed_ms": elapsed_ms,
        "manual_baseline_ms": _MANUAL_SEARCH_BASELINE_MS,
    }


class TagRequest(BaseModel):
    equipment_tag: str


@router.post("/reason")
def reason_endpoint(req: TagRequest):
    """Industrial Reasoning Engine: causal + temporal + episodic + planning →
    an operational-intelligence assessment for an equipment tag."""
    return reason(req.equipment_tag, dispatch=orchestrator.dispatch)


@router.post("/simulate")
def simulate_endpoint(req: TagRequest):
    """What-if failure simulation: project the ripple effects of an asset failure."""
    return simulate_failure(req.equipment_tag)


# ---- simulated sensor stream (historian stand-in) ----
from backend.core.sensor_stream import sensor_stream


@router.post("/stream/tick")
def stream_tick(req: TagRequest):
    """Advance the simulated sensor feed one step for an asset and return live
    readings + the real anomaly assessment. When the anomaly trips, the
    readings can be passed to /agents/dispatch maintenance for a live-risk
    diagnosis."""
    return sensor_stream.tick(req.equipment_tag)


@router.post("/stream/reset")
def stream_reset(req: TagRequest):
    sensor_stream.reset(req.equipment_tag)
    return {"reset": req.equipment_tag}


# ---- autonomous workflow (with human approval gate) ----
workflow = WorkflowEngine(
    notifier=lambda t, m, s: build_notification(t, m, s),
    memory=orchestrator.memory,
)


class ApprovalRequest(BaseModel):
    approver: str = "engineer"
    reason: str = ""


@router.post("/workorders/draft")
def draft_work_order(req: TagRequest):
    """Reason about the asset, then auto-draft a corrective work order — held
    at the human-approval gate (nothing executes until approved)."""
    assessment = reason(req.equipment_tag, dispatch=orchestrator.dispatch)
    if "error" in assessment:
        raise HTTPException(status_code=404, detail=assessment["error"])
    return workflow.create_from_assessment(assessment)


@router.get("/workorders")
def list_work_orders(status: str | None = None):
    return workflow.list_orders(status)


@router.post("/workorders/{order_id}/approve")
def approve_work_order(order_id: str, req: ApprovalRequest):
    try:
        return workflow.approve(order_id, req.approver)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/workorders/{order_id}/reject")
def reject_work_order(order_id: str, req: ApprovalRequest):
    try:
        return workflow.reject(order_id, req.approver, req.reason)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/knowledge/stats")
def knowledge_stats():
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


def _post_ingest(area: str) -> list[dict]:
    """Publish the document_ingested event so compliance + lessons react
    automatically (event-driven cascade)."""
    return bus.publish("document_ingested", {"area": area})


@router.post("/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)):
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
        "reactions": _post_ingest(safe_name),
    }


@router.post("/ingest/sample")
def ingest_sample():
    path = os.path.abspath(_SAMPLE_PDF)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Sample not found at {path}")
    result = ingest_pdf(path, graph=knowledge_graph, vector_store=vector_store)
    return {
        "source_doc": os.path.basename(result.source_doc),
        "pages_ingested": result.num_pages,
        "chunks_created": result.num_chunks,
        "entities_found": result.entities_found,
        "reactions": _post_ingest("plant"),
    }
