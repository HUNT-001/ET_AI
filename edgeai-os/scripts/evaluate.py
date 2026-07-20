"""
Evaluation harness — produces the concrete numbers PS8 judges ask for, against
the bundled sample report (swap in real documents + labels to strengthen).

Metrics:
  1. Entity-extraction precision/recall (equipment tags, regulatory refs)
  2. Retrieval hit@k on domain benchmark questions
  3. Time-to-answer vs. a manual-search baseline
  4. Compliance gap-detection precision/recall (planted known gaps)
  5. Knowledge-graph linkage (typed relationships built)
  6. Answer grounding coverage (VerifierAgent)

Run:  python scripts/evaluate.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import AgentRequest
from agents.ingestion_agent import IngestionAgent
from agents.compliance_agent import ComplianceAgent
from agents.reasoning_agent import Passage, synthesize
from agents.verifier_agent import verify_answer
from knowledge.entity_extraction import extract_entities
from knowledge.pdf_extract import extract_pdf_text
from knowledge.store import knowledge_graph, vector_store

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "datasets", "samples",
                      "sample_maintenance_report.pdf")

# Hand-labelled ground truth for the sample doc (high-signal entity types).
GROUND_TRUTH = {
    "equipment_tag": {"P-101A", "V-204", "PL-22"},
    "regulatory_reference": {"OISD-STD-118", "Factory Act Sec. 21"},
}
BENCHMARK_QUERIES = [
    ("What did the inspection find about the P-101A bearing?", "sample_maintenance_report"),
    ("OISD mandated safety distance requirement", "sample_maintenance_report"),
    ("relief valve V-204 set pressure verification", "sample_maintenance_report"),
    ("operating pressure on line PL-22", "sample_maintenance_report"),
]
EXPECTED_GAPS = {"PESO", "environmental_norms", "quality_standards"}
EXPECTED_COVERED = {"OISD", "Factory Act"}
MANUAL_BASELINE_MS = 8 * 60 * 1000


def _prf(pred: set, gold: set) -> dict:
    tp = len(pred & gold)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "tp": tp, "predicted": len(pred), "gold": len(gold)}


def evaluate() -> dict:
    report: dict = {}

    # ---- 1. Entity extraction P/R (unique values per type) ----
    doc = extract_pdf_text(SAMPLE)
    extracted: dict[str, set] = {}
    for e in extract_entities(doc.full_text):
        extracted.setdefault(e.entity_type, set()).add(e.value)
    report["entity_extraction"] = {
        t: _prf(extracted.get(t, set()), gold) for t, gold in GROUND_TRUTH.items()
    }

    # ---- ingest for retrieval / graph / compliance ----
    IngestionAgent().run(AgentRequest(task="ingest", payload={"path": SAMPLE}))

    # ---- 2. Retrieval hit@k ----
    k = 3
    hits = 0
    for q, expected in BENCHMARK_QUERIES:
        res = vector_store.search(q, top_k=k)
        if any(expected in os.path.basename(r.source_doc) for r in res):
            hits += 1
    report["retrieval"] = {"k": k, "queries": len(BENCHMARK_QUERIES),
                           "hits": hits, "hit_rate": round(hits / len(BENCHMARK_QUERIES), 3)}

    # ---- 3. Time-to-answer ----
    times = []
    for q, _ in BENCHMARK_QUERIES:
        t0 = time.perf_counter()
        res = vector_store.search(q, top_k=3)
        synthesize(q, [Passage(r.text, r.source_doc, r.page, r.similarity) for r in res])
        times.append((time.perf_counter() - t0) * 1000)
    avg_ms = round(sum(times) / len(times), 1)
    report["time_to_answer"] = {"avg_ms": avg_ms, "manual_baseline_ms": MANUAL_BASELINE_MS,
                                "speedup_x": round(MANUAL_BASELINE_MS / max(avg_ms, 1))}

    # ---- 4. Compliance gap detection ----
    comp = ComplianceAgent().run(AgentRequest(task="compliance", payload={"area": "Unit 3"})).result
    gaps = set(comp["coverage_gaps"])
    report["compliance_gap_detection"] = _prf(gaps, EXPECTED_GAPS)
    report["compliance_gap_detection"]["frameworks_covered"] = comp["frameworks_covered"]

    # ---- 5. Knowledge graph linkage ----
    report["knowledge_graph"] = knowledge_graph.stats()

    # ---- 6. Grounding coverage ----
    q = "What did the inspection find about the P-101A bearing?"
    res = vector_store.search(q, top_k=3)
    passages = [Passage(r.text, r.source_doc, r.page, r.similarity) for r in res]
    ans = synthesize(q, passages)["answer"]
    v = verify_answer(ans, passages)
    report["grounding"] = {"status": v["status"], "coverage": v["coverage"], "claims": v["claims"]}

    return report


def _print(report: dict) -> None:
    print("\n" + "=" * 60)
    print("  EdgeAI-OS — Evaluation Report")
    print("=" * 60)
    for t, m in report["entity_extraction"].items():
        print(f"  Entity [{t:<22}] P={m['precision']} R={m['recall']} F1={m['f1']}")
    r = report["retrieval"]
    print(f"  Retrieval hit@{r['k']}          : {r['hit_rate']}  ({r['hits']}/{r['queries']})")
    t = report["time_to_answer"]
    print(f"  Time-to-answer          : {t['avg_ms']} ms  (~{t['speedup_x']}x vs 8-min manual)")
    c = report["compliance_gap_detection"]
    print(f"  Compliance gap detection: P={c['precision']} R={c['recall']} F1={c['f1']}")
    g = report["knowledge_graph"]
    print(f"  Knowledge graph         : {g['total_entities']} entities, "
          f"{g['total_relationships']} typed links, {g['cross_document_entities']} cross-doc")
    gr = report["grounding"]
    print(f"  Answer grounding        : {gr['status']} (coverage {gr['coverage']})")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    rep = evaluate()
    _print(rep)
    out = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(rep, f, indent=2)
    print(f"Full results written to {os.path.relpath(out)}")
