"""
Industrial Reasoning Engine — the move from retrieval to operational intelligence.

Ordinary RAG answers "what is the vibration limit?". This engine answers
"given the vibration trend, the maintenance history, and the recurrence, here is
the likely failure path, how long you have, and what to do about it."

It composes four capabilities over the shared knowledge:
  1. Causal reasoning   — traverse the industrial failure-propagation ontology
  2. Temporal reasoning — the asset's dated history + recurrence
  3. Episodic memory    — "we've seen this before, and here's what worked"
  4. Planning           — recommend an action and a window (next planned outage)

Symbolic + grounded (rules/ontology/graph), narrated by the local LLM when
available and deterministically otherwise — so it always produces an
operational answer, never a hallucinated one.
"""

from __future__ import annotations

import re

from agents.base import AgentRequest
from knowledge import ontology
from knowledge.temporal import temporal_graph
from backend.core.episodic import episodic_memory

# Symptom → recommended corrective action / spare part.
_ACTION = {
    "vibration_elevated": ("bearing inspection / replacement", "bearing assembly"),
    "bearing_wear": ("bearing replacement", "bearing assembly"),
    "temperature_rise": ("lubrication check + bearing inspection", "lubricant + bearing assembly"),
    "lubrication_breakdown": ("re-lubrication and oil analysis", "lubricant"),
    "seal_failure": ("mechanical seal replacement", "mechanical seal kit"),
    "overpressure": ("relief-valve verification", "relief valve"),
    "recurrence": ("root-cause correction (not another temporary fix)", "as diagnosed"),
}
DEFAULT_OUTAGE_HOURS = 24  # assume next planned outage ~tomorrow


def reason(tag: str, dispatch=None) -> dict:
    """Produce an operational-intelligence assessment for an equipment tag."""
    tag = (tag or "").strip()
    if not tag:
        return {"error": "no equipment tag provided"}

    # 1. Current condition via MaintenanceAgent (risk + factors + RCA).
    if dispatch is not None:
        mres = dispatch("maintenance", tag, {"equipment_tag": tag}).result
    else:
        from agents.maintenance_agent import MaintenanceAgent
        mres = MaintenanceAgent().run(AgentRequest(task=tag, payload={"equipment_tag": tag})).result
    if not isinstance(mres, dict) or "risk" not in mres:
        return {"equipment_tag": tag, "error": "no data for this asset — ingest a document first."}

    factors = mres["risk"].get("factors", [])
    evidence_text = " ".join(factors) + " " + str(mres.get("rca_narrative", ""))

    # 2. Causal reasoning.
    taxonomy = ontology.classify_equipment(tag)
    symptoms = ontology.map_symptoms(evidence_text)
    causal = ontology.propagate(symptoms) if symptoms else {"primary_chain": [], "terminal": None, "hours_to_terminal": None}
    chain_text = ontology.describe_chain(causal.get("primary_chain") or [])

    # 3. Temporal reasoning.
    history = temporal_graph.history(tag)
    recurrence = temporal_graph.recurrence(tag)

    # 4. Episodic memory.
    precedent = episodic_memory.precedent(tag)

    # 5. Planning.
    hours = causal.get("hours_to_terminal")
    terminal_label = ontology.LABELS.get(causal.get("terminal"), causal.get("terminal") or "further degradation")
    primary_symptom = symptoms[0] if symptoms else None
    action, part = _ACTION.get(primary_symptom, ("inspection", "as diagnosed"))
    if precedent["seen_before"]:
        action = _ACTION.get("recurrence")[0]  # escalate to root-cause fix on recurrence
    schedule = ("during the next planned outage (~%dh) to minimize production impact" % DEFAULT_OUTAGE_HOURS
                if hours is None or hours > DEFAULT_OUTAGE_HOURS
                else "before the next shift — the projected window is shorter than the planned outage")

    recommendation = f"{action.capitalize()} on {tag}, scheduled {schedule}."

    # 6. Narrative (deterministic; the local LLM can polish it downstream).
    narrative = _narrate(tag, taxonomy, symptoms, chain_text, hours, terminal_label,
                         recurrence, precedent, recommendation, mres["risk"])

    return {
        "equipment_tag": tag,
        "equipment_class": taxonomy,
        "symptoms": [ontology.LABELS.get(s, s) for s in symptoms],
        "causal_chain": chain_text,
        "terminal_failure": terminal_label,
        "hours_to_elevated_risk": hours,
        "risk": mres["risk"],
        "temporal_history": history,
        "recurrence": recurrence,
        "precedent": precedent,
        "recommended_part": part,
        "recommendation": recommendation,
        "narrative": narrative,
    }


def _narrate(tag, taxonomy, symptoms, chain_text, hours, terminal_label,
             recurrence, precedent, recommendation, risk) -> str:
    cls = taxonomy.get("class", "asset")
    sym_txt = ", ".join(ontology.LABELS.get(s, s) for s in symptoms) or "the current readings"
    parts = [f"On {tag} ({cls}), {sym_txt} indicate active degradation (risk {risk.get('risk')})."]
    if chain_text:
        window = f"in ~{hours} h" if hours else "if left unaddressed"
        parts.append(f"The causal path {chain_text} reaches an elevated risk of {terminal_label} {window}.")
    if precedent.get("seen_before"):
        dates = ", ".join(precedent.get("dates") or []) or "previously"
        res = (precedent.get("prior_resolutions") or [None])[0]
        seen = f"This pattern has occurred before ({dates})"
        if res:
            res_clean = re.sub(r"^(resolved by|attributed to|recommend\w*)\s*", "", res.strip(), flags=re.I)
            seen += f"; prior fix on record: {res_clean.rstrip('.')}"
        parts.append(seen + " — the recurrence suggests the root cause was not fully addressed.")
    parts.append(recommendation)
    return " ".join(parts)


def populate_episodes_from_corpus() -> int:
    """Rebuild episodic memory from the ingested corpus (event-driven populator)."""
    from knowledge.store import vector_store
    from knowledge.entity_extraction import extract_entities
    import re as _re

    count = 0
    for c in getattr(vector_store, "_corpus", []):
        text = c.get("text", "")
        ents = extract_entities(text)
        tags = [e.value for e in ents if e.entity_type == "equipment_tag"]
        dates = [e.value for e in ents if e.entity_type == "date"]
        symptoms = ontology.map_symptoms(text)
        if not (tags and symptoms):
            continue
        m = _re.search(r"(recommend\w*|resolved by|attributed to)[^.]*\.", text, _re.I)
        resolution = " ".join(m.group(0).split()) if m else ""
        for tag in tags:
            episodic_memory.record(tag, ", ".join(ontology.LABELS.get(s, s) for s in symptoms),
                                   dates[0] if dates else "", resolution=resolution,
                                   source=c.get("source_doc", ""))
            count += 1
    return count
