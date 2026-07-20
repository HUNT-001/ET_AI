# EdgeAI-OS — Technical Status Report

**Project:** Industrial Knowledge Intelligence Platform
**Target:** ET AI Hackathon 2026 — Problem Statement 8 ("AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain"), with an eventual secondary submission to OSDHack
**Report date:** 12 July 2026
**Status:** Early-stage functional prototype — core ingestion/retrieval pipeline is real and tested; agent business logic beyond retrieval is still stubbed

---

## 1. Vision & Aim

### 1.1 What this aims to become
A reusable **Enterprise AI Intelligence Platform** — not a single-purpose app, but an orchestration layer (AI Orchestrator + shared memory + a knowledge graph + a set of specialized agents) that can be configured for a specific enterprise use case. The immediate configuration targets PS8: unifying an industrial plant's fragmented documents (engineering drawings, maintenance records, safety procedures, inspection reports, operating instructions) into one queryable, continuously-updated knowledge system.

### 1.2 Why this shape
The underlying problem, per the PS8 brief, is that asset-intensive organizations lose an estimated 35% of working hours to searching for information that already exists somewhere in the organization, across 7–12 disconnected document systems per plant, contributing to 18–22% of unplanned downtime. A retiring workforce (an estimated 25% of India's experienced industrial engineers within a decade) makes this worse — undocumented tribal knowledge disappears with them. The platform's job is to make that collective knowledge queryable, cited, and continuously updated, not to replace human judgment.

### 1.3 Two-stage rollout strategy
| Stage | Target | Priority | What changes |
|---|---|---|---|
| 1 | ET AI Hackathon (PS8) | Primary (committed) | Build enterprise-grade platform; cloud LLM APIs acceptable |
| 2 | OSDHack | Secondary, adapted later | Swap inference calls to a local runtime (Ollama/ONNX Runtime/llama.cpp) — architecture doesn't change, only the model call inside each agent |

**Constraint on record:** the hackathon rules require selecting exactly one problem statement per team. PS8 is the committed target; PS3 (Industrial EV Supply Chain & Asset Intelligence) was considered and set aside as a fallback, not a parallel submission.

---

## 2. Architecture (as built)

```
Client
  → FastAPI backend (backend/main.py)
  → AI Orchestrator (backend/core/orchestrator.py)
      → routes task to matching agent(s)
      → shares context via MemoryLayer (backend/core/memory.py)
  → Agent Layer (agents/)
      ├─ 5 PRIMARY agents (named explicitly in the PS8 brief)
      └─ 7 SUPPORTING agents (internal building blocks)
  → Knowledge Layer (knowledge/)
      ├─ PDF text extraction (pdfplumber)
      ├─ Entity extraction (regex, 5 PS8-named entity types)
      ├─ Knowledge graph (networkx, in-memory)
      └─ Vector store (ChromaDB, offline hashing embeddings)
```

### 2.1 Primary agents (PS8 "What You May Build" — direct name match)
| Agent | File | Maps to PS8 item | Status |
|---|---|---|---|
| `IngestionAgent` | `agents/ingestion_agent.py` | Universal Document Ingestion & Knowledge Graph Agent | **Real** |
| `KnowledgeAgent` | `agents/knowledge_agent.py` | Expert Knowledge Copilot | **Real (retrieval)**, extractive answers only |
| `MaintenanceAgent` | `agents/maintenance_agent.py` | Maintenance Intelligence & RCA Agent | Stub |
| `ComplianceAgent` | `agents/compliance_agent.py` | Quality & Regulatory Compliance Intelligence | Stub |
| `LessonsLearnedAgent` | `agents/lessons_learned_agent.py` | Lessons Learned & Failure Intelligence Engine | Stub |

### 2.2 Supporting agents (internal, not directly graded by name)
| Agent | Feeds into | Status |
|---|---|---|
| `PlannerAgent` | Orchestration across the 5 primary agents | Stub |
| `VisionAgent` | Ingestion (P&ID parsing, drawing digitisation) | Stub |
| `ReasoningAgent` | Knowledge, Maintenance (shared LLM calls) | Stub |
| `ForecastingAgent` | Maintenance (failure/degradation prediction) | Stub |
| `MonitoringAgent` | Maintenance (live condition signals) | Stub |
| `ReportingAgent` | Compliance (audit-ready evidence packages) | Stub |
| `NotificationAgent` | Lessons Learned (proactive warnings) | Stub |

### 2.3 Design principle in force
Every agent implements a common `BaseAgent` interface (`agents/base.py`): `AgentRequest` in, `AgentResponse` out (with `confidence`, `tool_calls`, `notes`/citations). The Orchestrator never touches model internals — only the model call inside each agent's `run()` method changes when swapping cloud→local inference later. This is what makes the Stage-1→Stage-2 rollout (Section 1.3) possible without a rewrite.

---

## 3. What Has Been Done (Completed, Verified)

All items below have been **executed and tested in this environment**, not just written — 9/9 automated tests currently pass (`pytest`).

### 3.1 Platform scaffold
- Full repository structure matching the original 10-phase setup plan: `backend/`, `agents/`, `knowledge/`, `models/`, `vector_db/`, `configs/`, `scripts/`, `tests/`, `docs/`, plus deployment-target placeholders (`frontend/`, `deployment/`, `firmware/`, `mobile/`, `desktop/`) reserved for Stage 2.
- `AI Orchestrator` + `MemoryLayer` (working/short-term/long-term/incident-archive interface, currently in-memory — see Section 5 for the production swap).
- FastAPI backend exposing `/health`, `/agents`, `/agents/primary`, `/orchestrate`, `/agents/dispatch`, `/memory`.
- `docker-compose.yml` for Postgres + Redis + Chroma (installed/configured, not yet wired into agent logic).
- MIT license, README, CONTRIBUTING, CHANGELOG — open-source readiness baseline for OSDHack's judging criteria.
- `pytest.ini` (`pythonpath = .`) so the test suite runs cross-platform (this fixed a real Windows-vs-Linux path-resolution issue encountered during setup).

### 3.2 Real document ingestion pipeline
- **PDF text extraction** (`knowledge/pdf_extract.py`, via `pdfplumber`) — handles text-native PDFs; raises a clear error on scanned/image-only PDFs rather than failing silently (OCR fallback not yet implemented — see Section 4).
- **Entity extraction** (`knowledge/entity_extraction.py`) — regex-based extraction across all 5 entity types named in the PS8 brief: `equipment_tag`, `process_parameter`, `regulatory_reference`, `personnel`, `date`. Tuned and corrected once already: an initial version misclassified report/log numbers (e.g. `MNT-2026`) as equipment tags; fixed via an explicit prefix exclusion list.
- **Knowledge graph** (`knowledge/graph_store.py`, via `networkx`) — in-memory graph; entities are deduplicated by `(type, value)` so the same equipment tag appearing across multiple documents resolves to one node (this is the mechanism behind PS8's "knowledge graph linkage completeness" evaluation criterion). Interface is deliberately Neo4j-swappable (Section 5).
- **Vector store** (`knowledge/vector_store.py`, via `ChromaDB`) — chunking + embedding + similarity search. Uses a custom **offline `HashingVectorizer`-based embedding function**, not Chroma's default — this was a necessary fix: Chroma's default embedding model downloads itself from the internet on first use, which fails on restricted-egress networks (encountered directly in this build environment, and a realistic risk on corporate/campus networks generally).
- **Pipeline orchestration** (`knowledge/pipeline.py`, `knowledge/store.py`) — ties extraction → entities → graph write → vector write into one call; a shared singleton store lets `IngestionAgent` writes and `KnowledgeAgent` reads see the same data within one running process.

### 3.3 Verified end-to-end behavior
A synthetic-but-realistic sample maintenance report (`datasets/samples/sample_maintenance_report.pdf`, original content, generated for testing) was ingested and queried live:
- Ingestion extracted **20 entities** across all 5 types from a single one-page document.
- Query *"What did the inspection find about pump P-101A bearing?"* correctly retrieved the relevant passage (confidence 0.475) with a citation to the exact source document and page number.
- Query *"OISD regulatory reference safety distance"* correctly retrieved the compliance section referencing OISD-STD-118 and Factory Act Sec. 21, not an unrelated passage.
- `docs/ProblemStatement.md` documents the PS8 brief's verbatim evaluation criteria, judging weights, and a first draft of benchmark questions to score future answers against.

### 3.4 Test coverage (9/9 passing)
| Test file | Covers |
|---|---|
| `tests/test_orchestrator.py` | Agent registry correctness, routing, dispatch, memory persistence |
| `tests/test_ingestion_pipeline.py` | Real ingestion (entity counts), knowledge graph population, retrieval relevance, citation presence |

---

## 4. What Needs To Be Done (Remaining Work, Prioritized)

### Priority 1 — Replace synthetic data with real documents
- [ ] Source 2–3 real documents (a real OISD standard, a real or realistic P&ID, real/realistically-anonymized maintenance logs). PS8's evaluation focus explicitly rewards validation against real industrial document samples over synthetic ones.
- [ ] Re-run ingestion against real documents and re-tune the entity-extraction regex patterns — they were built and tested against synthetic text and will encounter formatting variety (multi-column layouts, tables, headers/footers) that real scanned/exported documents introduce.
- [ ] Implement OCR fallback (PaddleOCR or EasyOCR) for scanned/image-only PDFs — the current pipeline explicitly rejects these rather than failing silently, but doesn't yet handle them.

### Priority 2 — Real LLM synthesis
- [ ] `KnowledgeAgent` currently returns the top retrieved passage **verbatim (extractive)**, not an LLM-synthesized answer. Needs a decision: cloud API (fastest path to working) vs. local via Ollama (more setup now, but converges with the eventual OSDHack requirement sooner).
- [ ] Once wired, validate against the benchmark questions in `docs/ProblemStatement.md`.

### Priority 3 — Make the remaining 3 primary agents real
- [ ] `MaintenanceAgent` — fuse `ForecastingAgent` (predictive failure model — start with LightGBM/XGBoost on realistic work-order data) + `MonitoringAgent` (live condition signals) + RCA reasoning over OEM manuals via `KnowledgeAgent`.
- [ ] `ComplianceAgent` — real regulatory-corpus RAG (Factory Act, OISD, PESO text) + gap detection against 2–3 test cases with a planted, known non-conformance.
- [ ] `LessonsLearnedAgent` — pattern-mining over the knowledge graph's incident-archive entities; hand off to `NotificationAgent` for proactive alerting.

### Priority 4 — Enterprise features
- [ ] Basic authentication (doesn't need to be production-grade for a demo, but should exist).
- [ ] Dashboard: agent status, knowledge graph visualization, compliance gap list, before/after time-to-answer comparison (the headline demo metric).
- [ ] Audit trail — log every automated answer/action for traceability (also a PS8-adjacent expectation given the compliance/audit framing).

### Priority 5 — Measure against PS8's actual evaluation criteria
- [ ] Entity extraction accuracy on a labeled test set.
- [ ] Time-to-answer vs. a manual-search baseline.
- [ ] Knowledge graph linkage completeness metric (cross-document entity resolution rate).
- [ ] Compliance gap detection precision/recall on planted test cases.

### Priority 6 — Submission packaging
- [ ] Architecture diagram (required deliverable).
- [ ] Presentation deck (required deliverable).
- [ ] Demo video (required deliverable).

### Priority 7 — Last, only after the above: OSDHack adaptation
- [ ] Swap cloud LLM calls for a local runtime (Ollama, Qwen 2.5 3B or Phi-4 Mini as a first target).
- [ ] Confirm `/health` and `/orchestrate` work fully offline.
- [ ] Package for at least one non-cloud deployment target (laptop is sufficient; Jetson/Raspberry Pi is a bonus, not a requirement).

---

## 5. Known Limitations (Technical Debt, Stated Honestly)

| Limitation | Why it's there | When to fix |
|---|---|---|
| Regex-based entity extraction, not ML-based NER | Fast to build, genuinely works on structured text, zero model dependency | If real documents show high false-positive/negative rates (Priority 1) |
| Offline `HashingVectorizer` embeddings instead of a real transformer model | Chroma's default embedding requires an internet download that fails on restricted networks | Once deployed somewhere with reliable model-download access, or once a local embedding model (via Ollama) is wired in |
| Knowledge graph is in-memory (`networkx`), not persisted | Zero infrastructure setup needed to demo today | Before any real deployment — swap for Neo4j (interface already designed to make this a contained change) |
| No OCR — text-native PDFs only | Scope control; most digitally-produced reports don't need it | Priority 1, once real scanned documents are in scope |
| `KnowledgeAgent` answers are extractive, not generated | No LLM wired in yet — deliberate sequencing decision | Priority 2 |
| No authentication, no audit trail yet | Not needed to prove the pipeline works | Priority 4, before any real demo involving sensitive data |
| Sliding-window chunking (800 chars, 150 overlap), not structure-aware | Simple, works for MVP | Revisit if answer quality suffers on longer, multi-section documents |
| Docker Desktop dependency for Postgres/Redis/Chroma-server was a real setup friction point (Windows npm-pipe error encountered during setup) | Docker Desktop must be running, not just installed | Not urgent — current pipeline doesn't require these services yet |

---

## 6. Improvisations & Future Enhancements (Backlog)

This section is a deliberate holding area for ideas that are **good but not currently prioritized** — things to revisit once the Priority 1–7 list above is substantially done, or if judging feedback/time budget opens room for them.

### Knowledge & retrieval quality
- Swap `HashingVectorizer` for a real sentence-transformer embedding model once a reliable model-download path exists (better semantic recall than the current hashing approach).
- Add true hybrid search (BM25 + vector), replacing the current simple keyword-overlap boost.
- Structure-aware chunking (by section/heading) instead of fixed-size sliding windows.
- LLM-based or spaCy-based NER as a second extraction pass for entities that don't follow strong lexical patterns (the current regex approach is weakest here).
- Confidence calibration — the current similarity-derived confidence score is a reasonable proxy but hasn't been validated against human judgment of "is this answer actually right."

### Platform & infrastructure
- Migrate `MemoryLayer` from in-memory to Redis (working/short-term) + Postgres (long-term/incident archive) — interfaces are already designed for this swap.
- Migrate `KnowledgeGraph` from `networkx` to Neo4j for real persistence and Cypher query power.
- CI/CD via GitHub Actions (lint + `pytest` on every push).
- Containerize the full backend (a proper `Dockerfile`, not just the database `docker-compose.yml`) for one-command deployment.
- Role-based access control (engineer vs. safety officer vs. auditor views) once auth exists.

### Agent capability
- Feedback loop: human validation on agent answers → periodic fine-tuning of the entity extractor / retrieval ranking (mirrors the "Continuous Learning" loop from the original platform vision).
- Multi-language support for field-technician queries (several other ET AI tracks emphasize regional-language interfaces — worth considering if the platform is pitched as broadly reusable later).
- Voice interface for field technicians (PS8 explicitly calls out mobile-first use for the Knowledge Copilot; voice is a natural extension).

### OSDHack-specific (Stage 2, not before Stage 1 is solid)
- Browser-only demo path via WebGPU/Transformers.js, independent of the Python backend.
- Edge hardware deployment (Jetson Orin Nano or Raspberry Pi 5) as a bonus proof point, not a requirement.
- TinyML/quantization exploration — explicitly deprioritized per the current strategy; revisit only after OSDHack's core "runs locally" requirement is satisfied by the simpler Ollama/ONNX Runtime swap.

---

## 7. Deliverables Checklist (Per PS8 Brief)

| Deliverable | Status |
|---|---|
| Working Prototype | Partial — ingestion + retrieval real; 3 of 5 primary agents still stubbed |
| Architecture Diagram | Not yet produced (content for it exists in Section 2 of this report and `docs/Architecture.md`) |
| Presentation Deck | Not started |
| Demo Video | Not started |

---

## 8. Repository Reference

```
edgeai-os/
├── agents/                  5 primary + 7 supporting agents, BaseAgent interface
├── backend/
│   ├── core/                orchestrator.py, memory.py
│   ├── api/                 routes.py (FastAPI endpoints)
│   └── main.py
├── knowledge/                REAL pipeline: pdf_extract, entity_extraction,
│                              graph_store, vector_store, pipeline, store
├── datasets/samples/          synthetic test PDF + generator script
├── docs/                      ProblemStatement.md, Architecture.md, Roadmap.md,
│                              TechStack.md, API.md, Deployment.md, this report
├── tests/                     9 tests, all passing
├── scripts/                   check_env.sh, generate_sample_pdf.py
├── docker-compose.yml         Postgres + Redis + Chroma (not yet wired in)
└── requirements.txt
```
