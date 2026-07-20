"""
Simulated sensor stream — a stand-in for a plant historian/SCADA feed.

Emits realistic per-asset readings (vibration mm/s, bearing temperature °C)
that drift upward with noise as a degradation scenario progresses. Each tick
appends readings to a rolling window and runs the REAL MonitoringAgent anomaly
detector over it — so the live-risk view in the dashboard is genuine detection
logic operating on a synthetic feed (clearly labeled), exactly where a real
historian (OSIsoft PI / OPC-UA) would plug in.
"""

from __future__ import annotations

import random
import time

from agents.monitoring_agent import detect_anomalies


class SensorStream:
    def __init__(self, seed: int = 7):
        self._rng = random.Random(seed)
        self._series: dict[str, dict] = {}   # tag -> {vibration: [], temperature: [], t0}

    def _ensure(self, tag: str) -> dict:
        if tag not in self._series:
            self._series[tag] = {"vibration": [], "temperature": [], "ticks": 0}
        return self._series[tag]

    def tick(self, tag: str, degrade: bool = True) -> dict:
        """Advance the scenario one step for `tag` and return current readings
        + live anomaly assessment. `degrade=True` drifts toward failure."""
        s = self._ensure(tag)
        s["ticks"] += 1
        t = s["ticks"]
        # Baselines with noise; degradation = slow drift, then a fault-onset
        # step after tick 30 (the classic bearing-failure signature: gradual
        # wear, then a sharp vibration/temperature jump when damage initiates).
        drift = (t * 0.02 if degrade else 0.0)
        fault = (degrade and t > 30)
        vib = round(2.8 + self._rng.uniform(-0.3, 0.3) + drift
                    + (2.5 if fault else 0.0), 2)                                # mm/s
        temp = round(58.0 + self._rng.uniform(-1.2, 1.2) + drift * 4
                     + (9.0 if fault else 0.0), 1)                               # °C
        s["vibration"].append(vib)
        s["temperature"].append(temp)
        s["vibration"] = s["vibration"][-40:]
        s["temperature"] = s["temperature"][-40:]

        # SPC-style assessment: alarm ONLY on the LATEST reading, judged against
        # the baseline window's control limits. Judging whole-series outliers
        # would let baseline noise trip the alarm, and a sustained fault would
        # dilute its own z-score by shifting the series statistics.
        def _assess(series: list) -> dict:
            import statistics
            if len(series) <= 12:
                return detect_anomalies(series)
            baseline, latest = series[:12], series[-1]
            mean, stdev = statistics.fmean(baseline), statistics.pstdev(baseline)
            if stdev == 0:
                return {"anomaly": False, "score": 0.0, "detail": "Flat baseline."}
            z = abs(latest - mean) / stdev
            anomaly = z >= 3.0  # 3σ action limit vs baseline
            return {"anomaly": anomaly, "score": round(min(1.0, z / 6.0), 3),
                    "detail": (f"latest reading {latest} is {z:.1f}σ from baseline"
                               if anomaly else "Latest reading within baseline control limits.")}

        vib_check = _assess(s["vibration"])
        temp_check = _assess(s["temperature"])
        anomaly = vib_check["anomaly"] or temp_check["anomaly"]
        score = round(max(vib_check["score"], temp_check["score"]), 3)
        return {
            "tag": tag,
            "tick": t,
            "readings": {"vibration_mms": vib, "temperature_c": temp},
            "window": {"vibration": s["vibration"][-10:], "temperature": s["temperature"][-10:]},
            "anomaly": anomaly,
            "score": score,
            "detail": vib_check["detail"] if vib_check["anomaly"] else temp_check["detail"],
            "simulated": True,
            "ts": time.time(),
        }

    def reset(self, tag: str) -> None:
        self._series.pop(tag, None)

    def latest_window(self, tag: str) -> list:
        s = self._series.get(tag)
        return list(s["vibration"]) if s else []


sensor_stream = SensorStream()
