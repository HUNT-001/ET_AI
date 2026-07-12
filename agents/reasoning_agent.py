"""
ReasoningAgent — the shared answer-synthesis engine used internally by
KnowledgeAgent (Expert Knowledge Copilot) and MaintenanceAgent (RCA).

Design: this agent turns a question + a set of retrieved passages into a
grounded, *cited* answer. It has two paths:

  1. Optional LLM synthesis. If an LLM backend is configured (see
     `_try_llm_synthesis`), it is asked to answer using ONLY the supplied
     passages and to cite [source_doc p.N] inline. This is the path that
     converges with the eventual OSDHack local-inference swap — only the
     `_try_llm_synthesis` body changes (cloud API today, Ollama later).

  2. Offline deterministic synthesis (default / fallback). With no model
     available (restricted-egress networks, this sandbox, an unconfigured
     laptop), it composes an extractive-but-structured answer: it selects
     the sentences across the passages that best match the question, orders
     them, and appends explicit citations. This is real, deterministic, and
     never silently breaks — so retrieval quality is always demoable.

The public contract is BaseAgent (AgentRequest -> AgentResponse) plus a
module-level `synthesize()` helper other agents call directly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from agents.base import AgentRequest, AgentResponse, BaseAgent

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "was", "were", "be", "with", "at", "by", "this", "that", "it", "as", "from",
    "what", "which", "did", "does", "do", "about", "any", "has", "have", "had",
}


@dataclass
class Passage:
    text: str
    source_doc: str
    page: int
    similarity: float = 0.0


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z0-9\-]+", text.lower()) if w not in _STOPWORDS and len(w) > 1}


def _short_name(path: str) -> str:
    return os.path.basename(path) if path else path


def _score_sentence(sentence: str, q_words: set[str]) -> float:
    s_words = _keywords(sentence)
    if not s_words:
        return 0.0
    return len(q_words & s_words) / (len(q_words) or 1)


def synthesize(question: str, passages: list[Passage], max_sentences: int = 4) -> dict:
    """Compose a grounded, cited answer from retrieved passages.

    Returns {"answer": str, "citations": [...], "mode": "llm"|"offline",
             "confidence": float}. Callers (KnowledgeAgent, MaintenanceAgent)
    use the dict directly."""
    if not passages:
        return {
            "answer": "No relevant source material was found for this question.",
            "citations": [],
            "mode": "offline",
            "confidence": 0.0,
        }

    citations = [
        {"source_doc": _short_name(p.source_doc), "page": p.page, "similarity": round(p.similarity, 4)}
        for p in passages
    ]

    llm_answer = _try_llm_synthesis(question, passages)
    if llm_answer is not None:
        return {
            "answer": llm_answer,
            "citations": citations,
            "mode": "llm",
            "confidence": round(max(p.similarity for p in passages), 4),
        }

    # ---- Offline deterministic synthesis ----
    q_words = _keywords(question)
    scored: list[tuple[float, str, Passage]] = []
    for p in passages:
        for sent in _SENTENCE_SPLIT.split(p.text.strip()):
            sent = sent.strip()
            if len(sent) < 15:
                continue
            score = _score_sentence(sent, q_words) + 0.05 * p.similarity
            if score > 0:
                scored.append((score, sent, p))

    scored.sort(key=lambda t: t[0], reverse=True)
    chosen = scored[:max_sentences] if scored else []

    if not chosen:
        # No sentence-level keyword overlap — fall back to the top passage.
        top = passages[0]
        answer = top.text.strip()
        used = [top]
    else:
        seen: set[str] = set()
        parts: list[str] = []
        used: list[Passage] = []
        for _, sent, p in chosen:
            key = sent[:60]
            if key in seen:
                continue
            seen.add(key)
            tag = f"[{_short_name(p.source_doc)} p.{p.page}]"
            parts.append(f"{sent} {tag}")
            if p not in used:
                used.append(p)
        answer = " ".join(parts)

    confidence = round(max(p.similarity for p in passages), 4)
    return {"answer": answer, "citations": citations, "mode": "offline", "confidence": confidence}


def reason_via(services, question: str, passages: list[Passage]) -> dict:
    """Synthesize an answer, preferring the orchestrator invocation path.

    If `services` is present (agent is running under the Orchestrator), call
    ReasoningAgent through `services.invoke` so the call is routed and logged
    centrally. If it's None (agent unit-tested in isolation), fall back to the
    local `synthesize()` — same result, no orchestrator required."""
    if services is not None:
        resp = services.invoke("reasoning", question, {
            "question": question,
            "passages": [
                {"text": p.text, "source_doc": p.source_doc, "page": p.page, "similarity": p.similarity}
                for p in passages
            ],
        })
        if isinstance(resp.result, dict):
            return resp.result
    return synthesize(question, passages)


def _try_llm_synthesis(question: str, passages: list[Passage]) -> str | None:
    """Attempt real LLM synthesis. Returns a synthesized answer string, or
    None if no LLM backend is available (the default in offline/restricted
    environments).

    To enable cloud synthesis: set EDGEAI_LLM=openai and OPENAI_API_KEY.
    To enable local synthesis later (OSDHack): set EDGEAI_LLM=ollama and
    point EDGEAI_OLLAMA_MODEL at a pulled model. Only this function changes
    between Stage 1 (cloud) and Stage 2 (local) — nothing else in the
    platform is aware of which backend answered.
    """
    backend = os.environ.get("EDGEAI_LLM", "").lower()
    if not backend:
        return None

    context = "\n\n".join(
        f"[{_short_name(p.source_doc)} p.{p.page}] {p.text.strip()}" for p in passages
    )
    prompt = (
        "You are an industrial knowledge copilot. Answer the question using "
        "ONLY the passages below. Cite sources inline as [file p.N]. If the "
        "passages do not contain the answer, say so.\n\n"
        f"PASSAGES:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
    )
    try:
        if backend == "openai":
            from openai import OpenAI  # type: ignore

            client = OpenAI()
            resp = client.chat.completions.create(
                model=os.environ.get("EDGEAI_OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return resp.choices[0].message.content
        if backend == "ollama":
            import requests  # type: ignore

            model = os.environ.get("EDGEAI_OLLAMA_MODEL", "qwen2.5:3b")
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("response")
    except Exception:
        # Any failure (no network, missing package, bad key) falls back to
        # offline synthesis rather than crashing the request.
        return None
    return None


class ReasoningAgent(BaseAgent):
    name = "reasoning"
    description = (
        "Shared answer-synthesis engine used internally by KnowledgeAgent "
        "(Expert Knowledge Copilot) and MaintenanceAgent (RCA) — turns a "
        "question plus retrieved passages into a grounded, cited answer. "
        "Optional LLM backend; deterministic offline synthesis by default."
    )
    tools: list[str] = ["llm_synthesis", "offline_synthesis"]

    def run(self, request: AgentRequest) -> AgentResponse:
        question = request.payload.get("question") or request.task
        raw = request.payload.get("passages", [])
        passages = [
            p if isinstance(p, Passage) else Passage(
                text=p.get("text", ""),
                source_doc=p.get("source_doc", "unknown"),
                page=p.get("page", -1),
                similarity=p.get("similarity", 0.0),
            )
            for p in raw
        ]
        out = synthesize(question, passages)
        # result is the full synthesis dict so callers invoking this agent
        # through the orchestrator get answer + citations + mode, not just text.
        return AgentResponse(
            agent_name=self.name,
            result=out,
            confidence=out["confidence"],
            tool_calls=[f"{out['mode']}_synthesis"],
            notes=f"mode={out['mode']}; citations={out['citations']}",
        )
