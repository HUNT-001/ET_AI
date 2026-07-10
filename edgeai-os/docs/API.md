# API Reference

Base URL (local): `http://localhost:8000`
Interactive docs (Swagger UI): `http://localhost:8000/docs`

## `GET /health`
Liveness check.
```json
{ "status": "ok" }
```

## `GET /agents`
Lists every registered agent and its description.
```json
[ { "name": "planner", "description": "..." }, ... ]
```

## `POST /orchestrate`
Routes a task to every agent that claims relevance, dispatches to each,
and returns all their responses.

Request:
```json
{ "task": "planner", "payload": { "goal": "inspect line 3" } }
```

Response: `list[AgentResponse]`
```json
[
  {
    "agent_name": "planner",
    "result": "...",
    "confidence": 0.0,
    "tool_calls": [],
    "notes": "..."
  }
]
```

## `POST /agents/dispatch`
Calls one specific agent directly, bypassing routing.

Request:
```json
{ "agent": "vision", "task": "detect_ppe_violation", "payload": { "image_url": "..." } }
```

Response: single `AgentResponse` (same shape as above).

## `GET /memory`
Dumps the current shared memory snapshot (working / short-term / long-term /
incident archive). Useful for debugging; will need auth before production use.
