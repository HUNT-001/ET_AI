"""
Temporal knowledge layer — time-aware facts.

Industrial plants are time-based: sensors, maintenance, failures and audits all
change. A static graph can't answer "what changed between June and July?" This
layer records observations as timestamped, versioned events so the platform can
reason over time: an asset's history, what changed in a window, and how often a
pattern recurs.

Deterministic in-memory store (demo); the same interface maps onto a
time-series DB (Timescale/InfluxDB) later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(\d{4})\b", re.I)


def parse_date(text: str):
    """Parse '14 March 2026' → datetime (UTC). Returns None if not found."""
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    day, mon, year = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
    try:
        return datetime(year, mon, day, tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass
class TemporalEvent:
    entity: str
    attribute: str
    value: str
    timestamp: datetime
    source: str
    confidence: float = 1.0


class TemporalGraph:
    def __init__(self) -> None:
        self._events: list[TemporalEvent] = []

    def record(self, entity: str, attribute: str, value: str, timestamp,
               source: str = "", confidence: float = 1.0) -> None:
        if isinstance(timestamp, str):
            timestamp = parse_date(timestamp)
        if timestamp is None:
            return
        self._events.append(TemporalEvent(entity, attribute, value, timestamp, source, confidence))

    def history(self, entity: str) -> list[dict]:
        evs = sorted((e for e in self._events if e.entity == entity), key=lambda e: e.timestamp)
        return [{"attribute": e.attribute, "value": e.value,
                 "date": e.timestamp.strftime("%d %b %Y"), "source": e.source} for e in evs]

    def changes_between(self, start, end) -> list[dict]:
        if isinstance(start, str):
            start = parse_date(start)
        if isinstance(end, str):
            end = parse_date(end)
        out = []
        for e in sorted(self._events, key=lambda e: e.timestamp):
            if start and e.timestamp < start:
                continue
            if end and e.timestamp > end:
                continue
            out.append({"entity": e.entity, "attribute": e.attribute, "value": e.value,
                        "date": e.timestamp.strftime("%d %b %Y"), "source": e.source})
        return out

    def recurrence(self, entity: str, attribute: str | None = None) -> dict:
        evs = [e for e in self._events if e.entity == entity
               and (attribute is None or e.attribute == attribute)]
        evs.sort(key=lambda e: e.timestamp)
        dates = sorted({e.timestamp.strftime("%d %b %Y") for e in evs},
                       key=lambda d: datetime.strptime(d, "%d %b %Y"))
        return {"count": len(evs), "dates": dates, "recurring": len(dates) >= 2}

    def stats(self) -> dict:
        return {"events": len(self._events),
                "entities": len({e.entity for e in self._events})}


# Process-wide temporal graph (shared with knowledge.store singletons).
temporal_graph = TemporalGraph()
