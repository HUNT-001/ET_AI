# Architecture

Target: ET AI Hackathon 2026, Problem Statement 8 (Industrial Knowledge
Intelligence). See `docs/ProblemStatement.md` for the full brief mapping.

## Layers

1. **User Applications** — dashboards, mobile app (Expert Knowledge Copilot
   is explicitly required to work on mobile for field technicians), browser
2. **AI Orchestrator** — request routing, agent scheduling, task planning,
   context/memory management (`backend/core/orchestrator.py`)
3. **Agent Layer** — 5 primary agents named explicitly in the PS8 brief,
   plus 7 supporting agents they call internally (`agents/`). See
   `docs/ProblemStatement.md` for the full mapping table.
   - Primary: Ingestion, Knowledge (Copilot), Maintenance (RCA), Compliance, Lessons Learned
   - Supporting: Planner, Vision (P&ID parsing), Reasoning (shared LLM), Forecasting, Monitoring, Reporting, Notification
4. **Memory Layer** — Working → Short-term → Long-term → Knowledge Graph →
   Vector DB → Historical → Incident Archive, shared across all agents
   (`backend/core/memory.py`)
5. **Knowledge Layer** — ingestion of engineering drawings, maintenance
   records, safety procedures, inspection reports, operating instructions,
   project files (PDFs, P&IDs, scanned forms, spreadsheets, email archives)
   → OCR → entity extraction (equipment tags, process parameters,
   regulatory references, personnel, dates) → knowledge graph → hybrid
   (vector + keyword) semantic index
6. **AI Intelligence Layer** — one small model per problem: LLM/SLM
   (Reasoning, shared), CV (P&ID/drawing parsing), forecasting
   (predictive maintenance), anomaly detection (real-time conditions),
   rule engine (regulatory compliance mapping)
7. **Enterprise Features** — dashboards, audit trails, compliance evidence
   packages, alerting — what judges actually see in the demo

## Explicitly out of scope for this build
PS8 does not ask for digital twin / simulation (unlike PS1, PS2, PS4 in
the same hackathon) — we deliberately dropped `simulation_agent` and
`optimization_agent` rather than carry unused surface area. If a later
pivot needs them, they're a straightforward re-add following the same
`BaseAgent` pattern.

## Request Flow (implemented)

Two entry points:

```
Single-intent (POST /orchestrate {task, payload})
  → Orchestrator.classify(task)        # intent classification → best-fit agent
  → Orchestrator.dispatch(agent, ...)  # builds AgentRequest w/ AgentServices + memory context
  → Agent.run(request)                 # may call other agents via request.services.invoke(...)
  → Orchestrator logs to MemoryLayer (short-term)
  → Client receives list[AgentResponse]

Multi-step goal (POST /plan {task, payload})
  → Orchestrator.dispatch("planner", goal)   # PlannerAgent → ordered [{agent, task, payload}]
  → Orchestrator.plan_and_execute(...)        # runs each step, threading results through memory
  → Client receives {goal, plan, results[]}
```

**AgentServices** is the key contract: the Orchestrator injects a `services`
handle (`invoke(agent, task, payload)` + shared `memory`) into every
`AgentRequest`. Agents call one another *through* it rather than importing
each other — so `MaintenanceAgent` gets `ForecastingAgent`/`MonitoringAgent`/
`ReasoningAgent` output via `services.invoke(...)`, and logs incidents to
`services.memory` that `LessonsLearnedAgent` later reads back. Routing,
logging, and future cross-cutting concerns stay centralized in the
Orchestrator. (Agents fall back to a local path when run without an
Orchestrator, so they remain unit-testable in isolation.)

Typical PS8 flow for a user question:
```
User query
  → KnowledgeAgent (Expert Knowledge Copilot)
      → hybrid search + knowledge graph query
      → ReasoningAgent (shared LLM) synthesises answer w/ citations
  → (if maintenance-related) MaintenanceAgent
      → ForecastingAgent (failure prediction) + MonitoringAgent (live conditions)
      → RCA reasoning over OEM manuals via KnowledgeAgent
  → (if compliance-related) ComplianceAgent
      → regulatory corpus RAG + knowledge graph comparison
      → ReportingAgent generates evidence package
  → LessonsLearnedAgent runs continuously in the background over the
    incident archive, pushing warnings via NotificationAgent
```

## Design Principle

**The deployment changes. The architecture doesn't.** Per the current
priority order, this platform is being built enterprise-first for ET AI
(cloud LLM APIs acceptable during development). Only in the final phase
does inference get swapped to a local runtime (Ollama/ONNX Runtime/
llama.cpp) for the OSDHack submission — agent and orchestrator code should
never need to change for that swap, only the model call inside each
agent's `run()` method.
