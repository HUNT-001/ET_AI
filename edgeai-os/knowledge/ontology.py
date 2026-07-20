"""
Industrial ontology + causal failure-propagation model.

This is the substrate that turns retrieval into *reasoning*. It encodes real
domain knowledge, curated (a rule/ontology engine, not a trained model, so it's
transparent and defensible):

  - an equipment taxonomy (pump → rotating_equipment → mechanical_asset), and
  - a causal failure-propagation graph — how a symptom escalates to a failure,
    by what mechanism, and over roughly what time horizon.

The Reasoning Engine traverses this to answer *"what does this observation lead
to, and how long do we have?"* — moving from information retrieval to
operational intelligence.
"""

from __future__ import annotations

# Equipment class from tag prefix → industry taxonomy (is-a hierarchy).
_PREFIX_CLASS = {
    "P": "pump", "PL": "pipeline", "V": "valve", "M": "motor",
    "C": "compressor", "HX": "heat_exchanger", "T": "tank",
}
_TAXONOMY = {
    "pump": ["rotating_equipment", "mechanical_asset"],
    "motor": ["rotating_equipment", "electrical_asset"],
    "compressor": ["rotating_equipment", "mechanical_asset"],
    "valve": ["flow_control", "mechanical_asset"],
    "pipeline": ["containment", "static_asset"],
    "heat_exchanger": ["thermal_asset", "static_asset"],
    "tank": ["containment", "static_asset"],
}

# Causal links: cause → effect, with mechanism, typical time-to-effect (hours),
# and severity (0..1). This is the failure-propagation graph.
CAUSAL_LINKS = [
    {"cause": "vibration_elevated", "effect": "bearing_wear",
     "mechanism": "mechanical fatigue from imbalance/misalignment", "ttl_hours": 168, "severity": 0.5},
    {"cause": "bearing_wear", "effect": "temperature_rise",
     "mechanism": "increased friction in the bearing housing", "ttl_hours": 72, "severity": 0.6},
    {"cause": "temperature_rise", "effect": "lubrication_breakdown",
     "mechanism": "oil viscosity loss above rated temperature", "ttl_hours": 48, "severity": 0.7},
    {"cause": "lubrication_breakdown", "effect": "seal_failure",
     "mechanism": "dry running degrades the mechanical seal", "ttl_hours": 24, "severity": 0.85},
    {"cause": "seal_failure", "effect": "unplanned_shutdown",
     "mechanism": "loss of containment forces a trip", "ttl_hours": 6, "severity": 1.0},
    {"cause": "overpressure", "effect": "relief_valve_lift",
     "mechanism": "operating pressure approaches rated maximum", "ttl_hours": 2, "severity": 0.7},
    {"cause": "relief_valve_lift", "effect": "unplanned_shutdown",
     "mechanism": "pressure excursion trips the unit", "ttl_hours": 4, "severity": 1.0},
    {"cause": "recurrence", "effect": "accelerated_degradation",
     "mechanism": "repeat fault indicates an unresolved root cause", "ttl_hours": 48, "severity": 0.8},
]

# Human-readable labels for failure/symptom nodes.
LABELS = {
    "vibration_elevated": "elevated vibration", "bearing_wear": "bearing wear",
    "temperature_rise": "bearing temperature rise", "lubrication_breakdown": "lubrication breakdown",
    "seal_failure": "mechanical seal failure", "unplanned_shutdown": "unplanned shutdown",
    "overpressure": "operating overpressure", "relief_valve_lift": "relief-valve lift",
    "recurrence": "recurring fault", "accelerated_degradation": "accelerated degradation",
}

_BY_CAUSE: dict[str, list[dict]] = {}
for _l in CAUSAL_LINKS:
    _BY_CAUSE.setdefault(_l["cause"], []).append(_l)


def classify_equipment(tag: str) -> dict:
    """Tag → {class, is_a:[...]} using the taxonomy."""
    import re
    m = re.match(r"^([A-Z]{1,3})-?\d", tag or "")
    prefix = m.group(1) if m else ""
    cls = _PREFIX_CLASS.get(prefix, "asset")
    return {"tag": tag, "class": cls, "is_a": _TAXONOMY.get(cls, ["asset"])}


import re as _re

# Observed-condition text → ontology symptom node.
_SYMPTOM_PATTERNS = [
    (_re.compile(r"vibration.*(over|above|exceed)|elevated vibration", _re.I), "vibration_elevated"),
    (_re.compile(r"temperature.*(over|above|exceed).*(normal|rated)|°c over", _re.I), "temperature_rise"),
    (_re.compile(r"pressure.*(100%|rated maximum|overpressure|exceed)", _re.I), "overpressure"),
    (_re.compile(r"recurr|again|prior|seen before|repeat", _re.I), "recurrence"),
    (_re.compile(r"lubric|oil (contamination|viscosity)", _re.I), "lubrication_breakdown"),
    (_re.compile(r"seal", _re.I), "seal_failure"),
]


def map_symptoms(text: str) -> list[str]:
    """Detect ontology symptom nodes present in free text (e.g. RCA factors)."""
    found = []
    for pat, node in _SYMPTOM_PATTERNS:
        if pat.search(text or "") and node not in found:
            found.append(node)
    return found


def propagate(symptoms: list[str], horizon_hours: int = 336) -> dict:
    """Forward-traverse the causal graph from observed symptoms to terminal
    failures, accumulating time-to-effect. Returns the chains, the earliest
    terminal failure, and the hours until it.

    Returns {chains:[[step,...]], terminal, hours_to_terminal, severity}."""
    chains: list[list[dict]] = []

    def walk(node: str, elapsed: float, path: list[dict], seen: set):
        links = _BY_CAUSE.get(node, [])
        if not links or elapsed > horizon_hours:
            if len(path) > 0:
                chains.append(path)
            return
        for link in links:
            if link["effect"] in seen:
                continue
            walk(link["effect"], elapsed + link["ttl_hours"],
                 path + [{**link, "elapsed_hours": round(elapsed + link["ttl_hours"])}],
                 seen | {link["effect"]})

    for s in symptoms:
        walk(s, 0.0, [], {s})

    # Earliest chain reaching unplanned_shutdown (or the most severe terminal).
    terminal_chains = [c for c in chains if c and c[-1]["effect"] == "unplanned_shutdown"]
    best = min(terminal_chains, key=lambda c: c[-1]["elapsed_hours"], default=None)
    if best is None:
        best = max(chains, key=lambda c: c[-1]["severity"], default=[])
    hours = best[-1]["elapsed_hours"] if best else None
    terminal = best[-1]["effect"] if best else None
    severity = best[-1]["severity"] if best else 0.0
    return {"chains": chains, "primary_chain": best, "terminal": terminal,
            "hours_to_terminal": hours, "severity": severity}


def describe_chain(chain: list[dict]) -> str:
    """Render a causal chain as readable text: A → B → C."""
    if not chain:
        return ""
    nodes = [LABELS.get(chain[0]["cause"], chain[0]["cause"])]
    for link in chain:
        nodes.append(LABELS.get(link["effect"], link["effect"]))
    return " → ".join(nodes)
