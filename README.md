# EdgeAI-OS

**A reusable Enterprise AI Intelligence Platform**, currently built for
**ET AI Hackathon 2026 — Problem Statement 8: "AI for Industrial Knowledge
Intelligence."** One AI Orchestrator, a shared memory layer, a knowledge
graph built from industrial documents, and 5 named agents matching the
brief's "What You May Build" list — designed so the same platform can later
be adapted to run fully on-device for OSDHack, without an architecture
rewrite.

See [`docs/ProblemStatement.md`](docs/ProblemStatement.md) for the graded
brief this build targets, and [`docs/Architecture.md`](docs/Architecture.md)
for the full design.

## Status

Early scaffold. The orchestrator, memory layer, and 12 agents (5 primary +
7 supporting) are wired up and tested end-to-end over a FastAPI backend.
Agents currently return placeholder responses — see
[`docs/Roadmap.md`](docs/Roadmap.md) for what's next, in priority order.

## Quickstart

```bash
# 1. Install Python deps
python3 -m venv .venv && source .venv/bin/activate   # or: uv venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) bring up Postgres + Redis + Chroma
docker compose up -d

# 3. Run the backend
uvicorn backend.main:app --reload --port 8000

# 4. Try it
curl http://localhost:8000/health
curl http://localhost:8000/agents
curl -X POST http://localhost:8000/orchestrate \
     -H "Content-Type: application/json" \
     -d '{"task": "planner", "payload": {"goal": "inspect line 3"}}'
```

Interactive API docs: http://localhost:8000/docs

## Repository Layout

| Folder | Purpose |
|---|---|
| `backend/` | FastAPI app: orchestrator, memory layer, API routes |
| `agents/` | The 11 specialized agents (Planner, Vision, Knowledge, ...) |
| `frontend/` | Next.js dashboard (to be scaffolded) |
| `models/` | Downloaded model weights (gitignored) |
| `knowledge/` | Document ingestion pipeline + knowledge graph build scripts |
| `vector_db/` | Vector store persistence / config |
| `configs/` | YAML/env configuration |
| `scripts/` | Setup and environment-check scripts |
| `docker/` | Dockerfiles per service |
| `deployment/` | Deployment targets: desktop, browser, edge, embedded |
| `firmware/`, `mobile/`, `desktop/` | Platform-specific runtime code |
| `tests/` | Test suite |
| `datasets/`, `notebooks/`, `benchmarks/` | R&D and evaluation |

## Documentation

- [Problem Statement (PS8 brief mapping)](docs/ProblemStatement.md)
- [Architecture](docs/Architecture.md)
- [Tech Stack](docs/TechStack.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/Deployment.md)
- [Roadmap](docs/Roadmap.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
