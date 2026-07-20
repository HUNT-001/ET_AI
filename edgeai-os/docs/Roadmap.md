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
- [x] **Real ingestion pipeline**: PDF text extraction (pdfplumber) →
      entity extraction (5 PS8 types, regex-based) → in-memory knowledge
      graph (networkx) → vector store (Chroma, offline hashing embeddings)
- [x] **Real retrieval**: `KnowledgeAgent` does hybrid search with
      citations (source doc + page) and similarity-based confidence
- [x] Tested end-to-end against a sample document (9/9 tests passing)

## Next — in priority order (enterprise-first, per current strategy)

### 1. Replace synthetic sample with real documents (do this first)
- [ ] Source 2-3 real documents: a real OISD standard PDF, a real or
      realistic P&ID, real (or realistically anonymized) maintenance logs
- [ ] Re-run ingestion against them, sanity-check entity extraction —
      the regex patterns were tuned on synthetic text and will need
      adjustment for real document formatting quirks
- [ ] Add OCR fallback (PaddleOCR) for any scanned/image-only PDFs —
      current pipeline only handles text-native PDFs

### 2. Wire real LLM synthesis into KnowledgeAgent
- [ ] Currently extractive (returns top retrieved passage verbatim) —
      swap in a real LLM call (cloud API for now, local later) that
      synthesizes an answer from the top-k retrieved chunks with inline
      citations, per the TODO in `agents/knowledge_agent.py`
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
