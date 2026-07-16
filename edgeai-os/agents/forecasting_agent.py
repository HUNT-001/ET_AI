"""
ForecastingAgent — equipment failure/degradation risk scoring.

Called internally by MaintenanceAgent, not directly by users.

Status: real, explainable heuristic model (NOT a stub). It scores
degradation risk from observed process parameters against typed thresholds
— temperature over normal range, vibration over baseline, operating
pressure approaching rated maximum, recurrence of prior anomalies. Every
score comes with the factors that produced it, so the recommendation is
auditable (a PS8 expectation).

This deliberately uses transparent rules rather than a trained model: a
LightGBM/XGBoost model on real work-order history is the Priority-3 upgrade
(see docs/Roadmap.md), and it will drop in behind this same
`score_degradation()` interface without changing MaintenanceAgent.
"""

from __future__ import annotations

import re

from agents.base import AgentRequest, AgentResponse, BaseAgent

# (regex, human factor template, weight) — each fires on a reading in the text.
_TEMP = re.compile(r"(\d+(?:\.\d+)?)\s*(?:degrees?\s*celsius|°c)", re.I)
_PRESSURE = re.compile(r"(\d+(?:\.\d+)?)\s*bar", re.I)
_VIBRATION_EXCEED = re.compile(r"exceed\w*\s+(?:the\s+)?baseline\s+(?:threshold\s+)?by\s+(\d+(?:\.\d+)?)\s*%", re.I)
_RATED_MAX = re.compile(r"rated\s+maximum\s+of\s+(\d+(?:\.\d+)?)\s*bar", re.I)
_NORMAL_TEMP = re.compile(r"(\d+(?:\.\d+)?)\s*degree[s]?\s*celsius\s*normal", re.I)
_RECURRENCE = re.compile(r"recurr\w+|similar\s+(?:vibration\s+)?anomaly|seen\s+(?:this\s+)?before|prior", re.I)


def score_degradation(text: str) -> dict:
    """Return {risk: 0..1, level: str, factors: [str]} from parameter readings
    found in `text` (typically an equipment's fused maintenance context)."""
    factors: list[str] = []
    risk = 0.0

    # Vibration exceedance over baseline — strong early-failure signal.
    vib = _VIBRATION_EXCEED.search(text)
    if vib:
        pct = float(vib.group(1))
        contrib = min(0.4, pct / 100.0 * 2.0)
        risk += contrib
        factors.append(f"Vibration {pct:.0f}% over baseline (bearing wear indicator) [+{contrib:.2f}]")

    # Temperature over stated normal operating range.
    normal_temp = _NORMAL_TEMP.search(text)
    temps = [float(m) for m in _TEMP.findall(text)]
    if normal_temp and temps:
        limit = float(normal_temp.group(1))
        over = [t for t in temps if t > limit]
        if over:
            worst = max(over)
            contrib = min(0.3, (worst - limit) / max(limit, 1) * 1.5)
            risk += contrib
            factors.append(f"Temperature {worst:.0f}°C over {limit:.0f}°C normal range [+{contrib:.2f}]")

    # Operating pressure approaching rated maximum.
    rated = _RATED_MAX.search(text)
    pressures = [float(m) for m in _PRESSURE.findall(text)]
    if rated and pressures:
        limit = float(rated.group(1))
        ratio = max(pressures) / limit if limit else 0
        if ratio >= 0.85:
            contrib = min(0.2, (ratio - 0.85) * 1.0 + 0.05)
            risk += contrib
            factors.append(f"Operating pressure at {ratio*100:.0f}% of rated maximum [+{contrib:.2f}]")

    # Recurrence of a prior anomaly — escalates urgency.
    if _RECURRENCE.search(text):
        risk += 0.2
        factors.append("Recurrence of a previously recorded anomaly [+0.20]")

    risk = round(min(1.0, risk), 3)
    level = "high" if risk >= 0.6 else "medium" if risk >= 0.3 else "low"
    if not factors:
        factors.append("No degradation indicators found in the available parameters.")
    return {"risk": risk, "level": level, "factors": factors}


class ForecastingAgent(BaseAgent):
    name = "forecasting"
    description = (
        "Equipment failure/degradation risk scoring for MaintenanceAgent. "
        "Explainable threshold-based model over process parameters "
        "(temperature, vibration, pressure, recurrence); upgradeable to a "
        "trained LightGBM/XGBoost model behind the same interface."
    )
    tools: list[str] = ["degradation_scorer"]

    def run(self, request: AgentRequest) -> AgentResponse:
        text = request.payload.get("context_text") or request.task
        out = score_degradation(text)
        return AgentResponse(
            agent_name=self.name,
            result=out,
            confidence=out["risk"],
            tool_calls=["degradation_scorer"],
            notes=f"level={out['level']}; factors={len(out['factors'])}",
        )
