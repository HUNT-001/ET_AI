# Target: ET AI Hackathon 2026 — Problem Statement 8

**"AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain"**

> Note: each team may select only one problem statement. PS8 is the
> committed target. PS3 ("AI for Industrial EV Supply Chain & Asset
> Intelligence") is a fallback option only — not a parallel submission.

## Challenge (as stated in the brief)
Build an AI-powered Industrial Knowledge Intelligence platform that ingests
heterogeneous documents — engineering drawings, maintenance records, safety
procedures, inspection reports, operating instructions, project files —
across structured and unstructured formats, and makes their collective
intelligence queryable, actionable, and continuously updated at the point
of need, across any device or function.

## The 5 named "What You May Build" agents (our primary deliverables)

| # | PS8 name | Our agent | File |
|---|---|---|---|
| 1 | Universal Document Ingestion & Knowledge Graph Agent | `IngestionAgent` | `agents/ingestion_agent.py` |
| 2 | Expert Knowledge Copilot | `KnowledgeAgent` | `agents/knowledge_agent.py` |
| 3 | Maintenance Intelligence & RCA Agent | `MaintenanceAgent` | `agents/maintenance_agent.py` |
| 4 | Quality & Regulatory Compliance Intelligence | `ComplianceAgent` | `agents/compliance_agent.py` |
| 5 | Lessons Learned & Failure Intelligence Engine | `LessonsLearnedAgent` | `agents/lessons_learned_agent.py` |

Everything else in `agents/` (`planner`, `vision`, `reasoning`,
`forecasting`, `monitoring`, `reporting`, `notification`) is a supporting
agent the primary 5 call internally — not part of PS8's named checklist,
but what makes the primary agents actually work. See `agents/__init__.py`
for the `PRIMARY_AGENTS` / `SUPPORTING_AGENTS` split.

## Suggested technologies (from the brief — treat as a checklist)
- [ ] RAG over heterogeneous industrial document corpora
- [ ] Knowledge Graphs & Industrial Ontology Engineering
- [ ] Computer Vision (P&ID parsing, drawing digitisation)
- [ ] OCR & Document Intelligence (structured + unstructured)
- [ ] Quality Management System (QMS) Integration
- [ ] Agentic AI for maintenance and compliance workflows

## Evaluation focus (what the demo needs to prove, verbatim from the brief)
1. **Entity extraction accuracy across document types** — need a small
   labeled test set (equipment tags, process parameters, regulatory refs,
   personnel, dates) to score against.
2. **Query answer quality on domain-expert benchmark questions** — write
   these benchmark Qs early; don't invent them last-minute. See
   "Benchmark questions" below.
3. **Knowledge graph linkage completeness** — % of extracted entities
   linked across ≥2 document types (e.g. an equipment tag appearing in
   both a P&ID and a maintenance log should resolve to one graph node).
4. **Time-to-answer vs. traditional search** — the classic before/after
   demo metric. Needs a manual-search baseline to compare against.
5. **Compliance gap detection accuracy** — construct test cases with a
   known, planted non-conformance to verify `ComplianceAgent` catches it.
6. **Cross-functional knowledge discovery improvement** — "ideally
   validated with real industrial document samples." See sourcing note.

## Judging criteria (weights)
| Criterion | Weight |
|---|---|
| Innovation | 25% |
| Business Impact | 25% |
| Technical Excellence | 20% |
| Scalability | 15% |
| User Experience | 15% |

## Real document sourcing (for evaluation focus #6)
The brief explicitly rewards validation against *real* industrial
documents, not purely synthetic ones. Candidates worth pulling in:
- **OISD standards** (Oil Industry Safety Directorate) — many published
  as public PDFs; directly matches the `REGULATORY_FRAMEWORKS` list in
  `compliance_agent.py`.
- **Factory Act, 1948** — public Indian legal text, good regulatory-RAG
  test corpus.
- **Public P&ID symbol libraries / sample drawings** — for `VisionAgent`
  testing without needing a real plant's proprietary drawings.
- Synthetic-but-realistic work orders / maintenance logs for anything
  that can't be sourced publicly (proprietary equipment history).

## Benchmark questions (draft — refine with domain input if possible)
Write 8-10 of these before the demo, spanning all 5 primary agents:
- "What is the OISD-mandated safety distance for [equipment class]?" (Knowledge/Compliance)
- "What was the root cause of the last three failures on [equipment tag]?" (Maintenance)
- "Which procedures reference [equipment tag] and are they current?" (Ingestion/Knowledge)
- "Are there any open compliance gaps for [area/unit]?" (Compliance)
- "Have we seen this failure pattern before, and where?" (Lessons Learned)

## Expected deliverables (per brief)
- Working Prototype
- Architecture Diagram
- Presentation Deck
- Demo Video
