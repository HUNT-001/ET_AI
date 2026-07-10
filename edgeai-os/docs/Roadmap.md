# Roadmap

Target: ET AI Hackathon 2026, Problem Statement 8 (Industrial Knowledge
Intelligence). See `docs/ProblemStatement.md` for the graded requirements
this roadmap is built against.

## Done
- [x] Repo structure (Phase 2)
- [x] Orchestrator + shared memory layer, tested end-to-end
- [x] 5 primary agents matching PS8's "What You May Build" by name:
      Ingestion, Knowledge (Copilot), Maintenance (RCA), Compliance,
      Lessons Learned — plus 7 supporting agents
- [x] FastAPI backend: `/health`, `/agents`, `/agents/primary`,
      `/orchestrate`, `/agents/dispatch`, `/memory`
- [x] docker-compose for Postgres + Redis + Chroma
- [x] Documentation set, including PS8 requirement mapping

## Next — in priority order (enterprise-first, per current strategy)

### 1. Make Ingestion + Knowledge Copilot real (highest leverage — do first)
- [ ] Pick 2-3 real document types to support first: PDF + CSV/spreadsheet
      + one P&ID sample — don't attempt all 5 source types before anything works
- [ ] Wire `IngestionAgent` to real OCR (PaddleOCR) + entity extraction
      tuned to the 5 named entity types (equipment tag, process parameter,
      regulatory reference, personnel, date)
- [ ] Stand up Neo4j, write real nodes/edges from ingested documents
- [ ] Wire `KnowledgeAgent` to hybrid search (Chroma + keyword) + an LLM
      (cloud API is fine for now) with mandatory inline citations
- [ ] Write the 8-10 benchmark questions from `docs/ProblemStatement.md`
      and start scoring answers against them

### 2. Compliance + Maintenance agents real
- [ ] Source real regulatory text (OISD standards, Factory Act) — see
      sourcing note in `docs/ProblemStatement.md`
- [ ] Wire `ComplianceAgent` to regulatory-corpus RAG + gap detection;
      build 2-3 test cases with a planted, known non-conformance
- [ ] Wire `MaintenanceAgent` to `ForecastingAgent` (start with a simple
      LightGBM/XGBoost model on synthetic-but-realistic work order data)

### 3. Lessons Learned + enterprise polish
- [ ] Wire `LessonsLearnedAgent` to pattern-mine the incident archive
- [ ] Auth (basic — doesn't need to be production-grade for a demo)
- [ ] Dashboard: agent status, knowledge graph visualization, compliance
      gap list, before/after time-to-answer comparison
- [ ] Audit trail — log every automated action/answer for traceability

### 4. Measure against PS8's evaluation focus
- [ ] Entity extraction accuracy on a labeled test set
- [ ] Time-to-answer vs. manual search baseline (the headline demo number)
- [ ] Knowledge graph linkage completeness metric
- [ ] Compliance gap detection precision/recall on planted test cases

### 5. Submission polish
- [ ] Architecture diagram (required deliverable)
- [ ] Presentation deck (required deliverable)
- [ ] Demo video (required deliverable)
- [ ] README screenshots

## Last — OSDHack adaptation (only after ET AI submission is solid)
- [ ] Swap cloud LLM calls in `ReasoningAgent`/`KnowledgeAgent` for a local
      runtime (Ollama with Qwen 2.5 3B or Phi-4 Mini first)
- [ ] Confirm `/health` and `/orchestrate` still work fully offline
- [ ] Package for one edge target (laptop is fine; Jetson/Pi is a bonus,
      not a requirement)
