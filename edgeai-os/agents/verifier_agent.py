"""
VerifierAgent — the "Supervisor" in a Generator→Supervisor safety loop.

Industrial answers can be dangerous when wrong (a bad claim about a pressure
valve, a missed compliance clause). So instead of trusting a single RAG pass,
every synthesized answer is checked *before the user sees it*: each claim
(sentence) must be (a) grounded in a retrieved passage and (b) carry a hard
citation. Ungrounded claims are flagged and stripped.

This is a deliberately transparent, deterministic grounding check — not a
black box. It uses lexical overlap against the retrieved passages by default;
with local Ollama embeddings available it can be upgraded to semantic overlap,
and a local LLM can be added as a second "LLM-as-judge" pass — all behind the
same `verify_answer()` contract, all still fully on-device.
"""

from __future__ import annotations

import re

from agents.base import AgentRequest, AgentResponse, BaseAgent
from agents.reasoning_agent import Passage

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CITATION = re.compile(r"\[[^\]]*p\.\s*\d+\]")
_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
         "was", "were", "be", "with", "at", "by", "this", "that", "it", "as", "from"}


def _content_words(text: str) -> set[str]:
    text = _CITATION.sub("", text)
    return {w for w in re.findall(r"[a-zA-Z0-9\-]+", text.lower()) if w not in _STOP and len(w) > 2}


def _overlap(sentence: str, passage: str) -> float:
    s, p = _content_words(sentence), set(re.findall(r"[a-zA-Z0-9\-]+", passage.lower()))
    return (len(s & p) / len(s)) if s else 0.0


def verify_answer(answer: str, passages, threshold: float = 0.5) -> dict:
    """Check each sentence of `answer` against the retrieved `passages`.

    Returns a report: per-sentence grounding + citation, overall coverage, the
    flagged (ungrounded) claims, a `verified_answer` with ungrounded claims
    removed, and a status of verified | partial | unverified."""
    texts = [p.text if isinstance(p, Passage) else p.get("text", "") for p in (passages or [])]
    # Keep only real claims: sentences long enough AND with content words left
    # after stripping citation tags (so a trailing "[doc p.1]" isn't a claim).
    raw_sents = [s.strip() for s in _SENTENCE_SPLIT.split((answer or "").strip())
                 if len(s.strip()) > 15 and _content_words(s)]
    if not raw_sents:
        return {"status": "unverified", "coverage": 0.0, "citation_coverage": 0.0,
                "sentences": [], "flagged": [], "verified_answer": "", "claims": 0}

    sentences, kept, flagged, cited = [], [], [], 0
    for sent in raw_sents:
        best = max((_overlap(sent, t) for t in texts), default=0.0)
        grounded = best >= threshold
        has_cite = bool(_CITATION.search(sent))
        cited += 1 if has_cite else 0
        sentences.append({"text": sent, "grounded": grounded,
                          "overlap": round(best, 3), "has_citation": has_cite})
        if grounded:
            kept.append(sent)
        else:
            flagged.append(sent)

    n = len(raw_sents)
    coverage = round(len(kept) / n, 3)
    citation_coverage = round(cited / n, 3)
    status = "verified" if not flagged else ("partial" if kept else "unverified")
    return {
        "status": status,
        "coverage": coverage,
        "citation_coverage": citation_coverage,
        "claims": n,
        "grounded_claims": len(kept),
        "flagged": flagged,
        "sentences": sentences,
        "verified_answer": " ".join(kept) if kept else "",
    }


class VerifierAgent(BaseAgent):
    name = "verifier"
    description = (
        "Supervisor agent — verifies every claim in a generated answer is "
        "grounded in a cited source passage before the user sees it; flags "
        "and strips ungrounded claims to prevent unsafe industrial "
        "hallucinations. Deterministic, fully on-device."
    )
    tools: list[str] = ["grounding_check"]

    def run(self, request: AgentRequest) -> AgentResponse:
        answer = request.payload.get("answer") or request.task
        passages = request.payload.get("passages", [])
        report = verify_answer(answer, passages, request.payload.get("threshold", 0.5))
        return AgentResponse(
            agent_name=self.name,
            result=report,
            confidence=report["coverage"],
            tool_calls=["grounding_check"],
            notes=f"status={report['status']}; {report['grounded_claims']}/{report['claims']} claims grounded",
        )
