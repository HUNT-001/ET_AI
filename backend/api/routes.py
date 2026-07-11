from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


class TaskRequest(BaseModel):
    task: str
    payload: dict = {}


class DispatchRequest(BaseModel):
    agent: str
    task: str
    payload: dict = {}


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
    """Route a task to whichever agent(s) claim it, and return all responses."""
    responses = orchestrator.handle(req.task, req.payload)
    return [r.__dict__ for r in responses]


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
