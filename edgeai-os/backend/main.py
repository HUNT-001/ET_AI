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
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="EdgeAI-OS",
    description="Universal AI Orchestration Layer — Enterprise + Edge AI reference platform.",
    version="0.1.0",
)

# Allow the single-file dashboard (opened from disk or served anywhere) to call
# this API from the browser. Permissive by design for the demo; tighten
# allow_origins to the deployed dashboard origin before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"name": "EdgeAI-OS", "status": "running", "docs": "/docs"}
