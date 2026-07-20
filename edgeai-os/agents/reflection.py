"""
Reflection loop — closes the Generator→Supervisor→Reflect cycle.

After an answer is synthesized and verified, if the VerifierAgent flags
ungrounded claims the system doesn't just return a weak answer: it reflects
("that wasn't fully grounded") and retries once with expanded retrieval, then
keeps whichever attempt is better-grounded. This measurably improves answer
reliability — exactly the failure mode (confident-but-unsupported answers) that
matters most in an industrial setting.
"""

from __future__ import annotations

import os

from agents.reasoning_agent import Passage, reason_via
from agents.verifier_agent import verify_answer


def answer_with_reflection(query: str, search_fn, top_k: int = 3, services=None,
                           expand_by: int = 3) -> dict:
    """`search_fn(query, top_k) -> list[SearchResult]`. Returns
    {answer, citations, confidence, mode, verification, reflected, attempts}."""
    def attempt(k: int) -> dict:
        results = search_fn(query, k)
        passages = [Passage(r.text, r.source_doc, r.page, r.similarity) for r in results]
        synth = reason_via(services, query, passages)
        verification = verify_answer(synth["answer"], passages)
        return {"synth": synth, "verification": verification, "passages": passages}

    first = attempt(top_k)
    reflected = False
    best = first
    if first["verification"]["status"] != "verified":
        second = attempt(top_k + expand_by)
        reflected = True
        # Keep whichever attempt grounds more of its claims.
        if second["verification"]["coverage"] >= first["verification"]["coverage"]:
            best = second

    synth, verification = best["synth"], best["verification"]
    sources = [
        {"source_doc": os.path.basename(p.source_doc), "page": p.page,
         "similarity": round(p.similarity, 4), "text": p.text}
        for p in best["passages"]
    ]
    return {
        "answer": synth["answer"],
        "citations": synth["citations"],
        "sources": sources,
        "confidence": synth["confidence"],
        "mode": synth["mode"],
        "verification": verification,
        "reflected": reflected,
        "attempts": 2 if reflected else 1,
    }
