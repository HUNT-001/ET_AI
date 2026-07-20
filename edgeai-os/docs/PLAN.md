# EdgeAI-OS — Prioritized Action Plan (PS8)

**Updated:** 12 July 2026 · **Target:** ET AI Hackathon 2026, Problem Statement 8

This plan supersedes the "What Needs To Be Done" section of `StatusReport.md`
for day-to-day execution. It is ordered by return-on-effort against PS8's
judging weights (Innovation 25% · Business Impact 25% · Technical Excellence
20% · Scalability 15% · User Experience 15%).

> **Deadline note:** slot the calendar dates below against your actual
> submission deadline. The ordering assumes you finish top-to-bottom and can
> stop at any point with a coherent, demoable system.

---

## 0. Done this session (was pending, now real)

All five PS8-named agents now execute real logic; the 4 supporting agents they
depend on are implemented; the full test suite (16 tests) passes.

- **KnowledgeAgent** — now synthesizes a composed, cited answer (via the shared
  ReasoningAgent) instead of returning one verbatim passage. Works offline;
  auto-upgrades to an LLM if `EDGEAI_LLM=openai|ollama` is set.
- **MaintenanceAgent** — real RCA pipeline: knowledge-graph asset lookup →
  passage retrieval → explainable degradation risk score → cited RCA narrative
  → prioritized recommendation. (Demo: P-101A returns HIGH risk 0.90 with the
  four contributing factors listed.)
- **ComplianceAgent** — real gap detection: expected vs. referenced regulatory
  frameworks → coverage gaps, plus recorded quality deviations, plus an
  auto-generated audit-ready evidence package. (Demo: surfaces PESO /
  environmental / quality gaps and the vibration exceedance.)
- **LessonsLearnedAgent** — real pattern mining over the knowledge graph
  (cross-document linkage + recurrence language) → severity-routed proactive
  warnings via NotificationAgent.
- **Supporting agents** — ReasoningAgent (offline+LLM synthesizer),
  ForecastingAgent (explainable degradation model), ReportingAgent (evidence
  packages), NotificationAgent (severity routing) are all real.
- **Quality fixes** — regulatory refs (OISD-STD-118) no longer misread as
  equipment tags; knowledge graph now stores real co-occurrence relationships;
  ChromaDB embedding function is forward-compatible.

**Deliverables status:** Working Prototype → now substantially complete (5/5
primary agents real). Architecture Diagram + Deck → produced this session (see
`docs/architecture_diagram.svg`, and the deck). Demo Video → still to record.

---

## 1. Priority 1 — Real documents (biggest score lever: Business Impact + Innovation)

PS8 explicitly rewards validation on *real* industrial documents over synthetic.
This is the single highest-value remaining task.

- Source 2–3 real/realistic documents: a real OISD standard PDF, a real or
  realistic P&ID, and anonymized maintenance logs. Add a second document that
  shares an equipment tag with the first — this is what makes cross-document
  knowledge-graph linkage (and LessonsLearned's strongest signal) demonstrable.
- Re-run ingestion; re-tune entity regex against real formatting (multi-column,
  tables, headers/footers).
- Implement OCR fallback (PaddleOCR/EasyOCR) for scanned/image-only PDFs.

## 2. Priority 2 — Turn on LLM synthesis for the demo (Technical Excellence + UX)

- The synthesis path is wired and offline-safe today. For the live demo, set
  `EDGEAI_LLM=openai` (or `ollama` for a local model) so answers read as fluent
  prose rather than stitched sentences. Nothing else changes.
- Validate answers against the benchmark questions in `docs/ProblemStatement.md`.

## 3. Priority 3 — Dashboard / UX (15% weight, currently the weakest axis)

- Minimal web dashboard: agent status, knowledge-graph visualization, compliance
  gap list, and the headline **before/after time-to-answer** metric.
- This is disproportionately valuable — UX is 15% and there is currently no UI.

## 4. Priority 4 — Measure against PS8's evaluation criteria (Technical Excellence)

- Small labeled test set → entity-extraction accuracy.
- Time-to-answer vs. a manual-search baseline (the headline demo number).
- Knowledge-graph linkage completeness (cross-document resolution rate).
- Compliance gap-detection precision/recall on a planted non-conformance case.

## 5. Priority 5 — Enterprise hardening (Scalability, 15%)

- Basic auth + an audit trail of every automated answer/action.
- Persist the knowledge graph (Neo4j) and memory (Redis/Postgres) — interfaces
  are already designed for the swap.

## 6. Priority 6 — Submission packaging

- Record the demo video (script it around: ingest → ask → RCA → compliance gap →
  proactive warning, showing citations throughout).
- Finalize the deck and architecture diagram against the real-document demo.

## 7. Priority 7 — OSDHack adaptation (only after Stage 1 is solid)

- Swap cloud LLM calls for a local runtime (set `EDGEAI_LLM=ollama`); confirm
  `/health` and `/orchestrate` run fully offline; package one non-cloud target.

---

## Suggested sequencing

1. Real documents + re-tune (P1) — unlocks the most credible demo.
2. LLM synthesis on (P2) — one env var; big perceived-quality jump.
3. Dashboard (P3) — closes the weakest judging axis.
4. Metrics (P4) — gives you concrete numbers to claim on stage.
5. Record video + finalize deck (P6).
6. Auth/persistence (P5) and OSDHack (P7) as time allows.

If time is very short, do **P1 → P2 → record video**: that alone is a coherent,
real-document, LLM-backed, cited-answer demo of all five agents.
