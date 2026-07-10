"""
EdgeAI-OS backend entrypoint.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Then try:
    curl http://localhost:8000/health
    curl http://localhost:8000/agents
    curl -X POST http://localhost:8000/orchestrate \\
         -H "Content-Type: application/json" \\
         -d '{"task": "planner", "payload": {}}'
"""

from fastapi import FastAPI

from backend.api.routes import router

app = FastAPI(
    title="EdgeAI-OS",
    description="Universal AI Orchestration Layer — Enterprise + Edge AI reference platform.",
    version="0.1.0",
)

app.include_router(router)


@app.get("/")
def root():
    return {"name": "EdgeAI-OS", "status": "running", "docs": "/docs"}
