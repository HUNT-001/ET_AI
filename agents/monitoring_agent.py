"""
MonitoringAgent — real-time condition / anomaly detection over sensor or log
streams, feeding MaintenanceAgent's live-condition context (supporting role).

Status: real (not a stub) for the detection logic. Given a series of readings
it flags anomalies with a z-score test (robust, zero-training, fully offline);
if scikit-learn is available and the series is long enough it additionally
runs an IsolationForest as a second opinion. Returns a normalized anomaly
score in 0..1 plus the offending values, so MaintenanceAgent can fuse it into
a risk score and cite *why*.

No live plant feed is wired in a demo, so this agent operates on readings
passed in `payload["readings"]`; with none, it reports "no live signal" rather
than fabricating one.
"""

from __future__ import annotations

import statistics

from agents.base import AgentRequest, AgentResponse, BaseAgent


def detect_anomalies(readings: list, z_threshold: float = 2.0) -> dict:
    """Flag anomalies in a 1-D numeric series against a 2σ warning band
    (SPC convention: 2σ = warning, 3σ = action).

    Returns {anomaly: bool, score: 0..1, method: str, outliers: [...],
             detail: str}. `score` is the max |z| seen, squashed into 0..1."""
    nums = [float(x) for x in (readings or []) if _is_number(x)]
    if len(nums) < 3:
        return {"anomaly": False, "score": 0.0, "method": "none",
                "outliers": [], "detail": "No live signal (need ≥3 numeric readings)."}

    mean = statistics.fmean(nums)
    stdev = statistics.pstdev(nums)
    if stdev == 0:
        return {"anomaly": False, "score": 0.0, "method": "zscore",
                "outliers": [], "detail": "Flat signal — no variance, no anomaly."}

    z_scores = [(x, abs(x - mean) / stdev) for x in nums]
    outliers = [x for x, z in z_scores if z >= z_threshold]
    max_z = max(z for _, z in z_scores)
    score = round(min(1.0, max_z / 6.0), 3)  # 6σ → saturates at 1.0

    method = "zscore"
    # Optional second opinion if sklearn is present and series is long enough.
    if len(nums) >= 12:
        try:
            from sklearn.ensemble import IsolationForest  # type: ignore

            model = IsolationForest(contamination="auto", random_state=0)
            preds = model.fit_predict([[x] for x in nums])
            iso_outliers = [nums[i] for i, p in enumerate(preds) if p == -1]
            if iso_outliers:
                outliers = sorted(set(outliers) | set(iso_outliers))
                method = "zscore+isolation_forest"
        except Exception:
            pass

    anomaly = bool(outliers)
    detail = (f"{len(outliers)} anomalous reading(s): {outliers}" if anomaly
              else "Readings within normal variation.")
    return {"anomaly": anomaly, "score": score if anomaly else round(min(0.3, score), 3),
            "method": method, "outliers": outliers, "detail": detail}


def _is_number(x) -> bool:
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


class MonitoringAgent(BaseAgent):
    name = "monitoring"
    description = (
        "Real-time condition/anomaly detection (z-score + optional Isolation "
        "Forest) over sensor/log readings, feeding MaintenanceAgent's "
        "live-condition context — supporting role."
    )
    tools: list[str] = ["zscore_detector", "isolation_forest"]

    def run(self, request: AgentRequest) -> AgentResponse:
        readings = request.payload.get("readings", [])
        out = detect_anomalies(readings)
        return AgentResponse(
            agent_name=self.name,
            result=out,
            confidence=out["score"],
            tool_calls=[out["method"]] if out["method"] != "none" else [],
            notes=out["detail"],
        )
