"""
Episodic / long-term organizational memory.

Ordinary RAG treats every query as independent. Real plants have institutional
history: this asset failed this way before, and here's what was done. This store
remembers episodes — a symptom/failure on an asset, when, and how it was
resolved — so the Reasoning Engine can say "this pattern occurred twice before
(2023, 2024); last time it was a loose foundation bolt." That's the retiring-
engineer knowledge the PS8 brief cares about, made durable.

In-memory for the demo; maps onto Postgres later behind the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Episode:
    equipment: str
    symptom: str
    date: str = ""
    resolution: str = ""
    outcome: str = ""
    source: str = ""


class EpisodicMemory:
    def __init__(self) -> None:
        self._episodes: list[Episode] = []

    def record(self, equipment: str, symptom: str, date: str = "",
               resolution: str = "", outcome: str = "", source: str = "") -> None:
        ep = Episode(equipment, symptom, date, resolution, outcome, source)
        # Dedupe: re-ingesting the same document shouldn't inflate recurrence.
        if any(vars(e) == vars(ep) for e in self._episodes):
            return
        self._episodes.append(ep)

    def recall(self, equipment: str) -> list[dict]:
        return [vars(e) for e in self._episodes if e.equipment == equipment]

    def precedent(self, equipment: str, symptom: str | None = None) -> dict:
        eps = [e for e in self._episodes if e.equipment == equipment
               and (symptom is None or symptom.lower() in e.symptom.lower())]
        seen_dates = list(dict.fromkeys(e.date for e in eps if e.date))
        seen_res = list(dict.fromkeys(e.resolution for e in eps if e.resolution))
        return {
            "equipment": equipment,
            "seen_before": len(eps) >= 1,
            "occurrences": len(eps),
            "dates": seen_dates,
            "prior_resolutions": seen_res,
            "episodes": [vars(e) for e in eps],
        }

    def stats(self) -> dict:
        return {"episodes": len(self._episodes),
                "assets": len({e.equipment for e in self._episodes})}


# Process-wide episodic memory.
episodic_memory = EpisodicMemory()
