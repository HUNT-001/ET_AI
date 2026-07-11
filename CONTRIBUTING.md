# Contributing

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
uvicorn backend.main:app --reload --port 8000
```

## Adding a new agent
1. Create `agents/<name>_agent.py`, subclass `BaseAgent` from `agents/base.py`.
2. Implement `run(self, request: AgentRequest) -> AgentResponse`.
3. Register it in `agents/__init__.py` (import + add to `REGISTRY`).
4. Add a test in `tests/`.

## Code style
- Python 3.12+, type hints required on public functions.
- Keep agents stateless where possible — shared state belongs in `MemoryLayer`.

## Tests
```bash
pytest
```

## Commit messages
Conventional commits preferred (`feat:`, `fix:`, `docs:`, `chore:`).
