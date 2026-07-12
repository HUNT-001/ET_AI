"""
Entity extraction over the 5 types named explicitly in the PS8 brief:
equipment_tag, process_parameter, regulatory_reference, personnel, date.

MVP implementation: regex/pattern-based. This is genuinely real (not a
stub) and works well for structured industrial text -- equipment tags and
regulatory references in particular follow strong lexical patterns. Swap
in an LLM-based or spaCy NER model later for looser prose extraction;
the ExtractedEntity interface below won't need to change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExtractedEntity:
    entity_type: str   # one of agents.ingestion_agent.ENTITY_TYPES
    value: str
    span: tuple[int, int]  # character offsets in the source chunk


# Equipment tags: letter(s)-digits(-optional letter), e.g. P-101A, V-204, PL-22
# Deliberately excludes common report/log-number prefixes (MNT, RPT, LOG, DOC)
# so report numbers like "MNT-2026-0142" aren't misread as equipment.
# STD/SEC excluded so regulatory refs like OISD-STD-118 / Factory Act Sec. 21
# aren't misclassified as equipment tags.
_NON_EQUIPMENT_PREFIXES = {"MNT", "RPT", "LOG", "DOC", "WO", "RFI", "STD", "SEC"}
_EQUIPMENT_TAG_RAW = re.compile(r"\b([A-Z]{1,3})-(\d{2,4})([A-Z]?)\b")


def _find_equipment_tags(text: str) -> list[re.Match]:
    return [
        m for m in _EQUIPMENT_TAG_RAW.finditer(text)
        if m.group(1) not in _NON_EQUIPMENT_PREFIXES
    ]

# Regulatory references: OISD-STD-###, "Factory Act Sec. ##", PESO refs
_REGULATORY_REF = re.compile(
    r"\bOISD-[A-Z]+-\d+\b|\bFactory Act Sec\.?\s*\d+[A-Za-z]?\b|\bPESO[- ][A-Za-z0-9\-]+\b"
)

# Dates: "14 March 2026", "09 March 2026", etc.
_DATE = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b"
)

# Process parameters: number + unit patterns common in industrial reports
_PROCESS_PARAM = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:bar|psi|°C|degrees? Celsius|kPa|rpm|%)\b"
)

# Personnel: "Name, Role" pattern -- e.g. "R. Menon, Senior Process Safety Engineer"
_PERSONNEL = re.compile(r"\b[A-Z]\.\s?[A-Z][a-z]+,\s[A-Z][a-zA-Z ]+\b")


PATTERNS: dict[str, re.Pattern] = {
    "regulatory_reference": _REGULATORY_REF,
    "date": _DATE,
    "process_parameter": _PROCESS_PARAM,
    "personnel": _PERSONNEL,
}


def extract_entities(text: str) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    for m in _find_equipment_tags(text):
        entities.append(ExtractedEntity(entity_type="equipment_tag", value=m.group(0), span=m.span()))

    for entity_type, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            entities.append(ExtractedEntity(entity_type=entity_type, value=m.group(0), span=m.span()))
    return entities
