"""
Autonomous workflow engine — work orders with a human-approval gate.

The step beyond answering: when the Reasoning Engine finds a high-risk
condition, the platform doesn't just alert — it drafts the corrective work
order (asset, action, parts, priority, schedule), holds it at the human
approval gate (industrial AI must not self-execute), and on approval executes
each step with a full audit trail: notify the maintenance lead, reserve spare
parts, log the incident, commit to organizational memory, and hand off to the
external CMMS/SAP adapter.

The external hop is a pluggable adapter (MockCMMSAdapter here; a real SAP/
Maximo adapter implements the same two methods). Everything else — lifecycle,
state, approval, audit — is real state managed by this engine.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field


class MockCMMSAdapter:
    """Reference adapter marking the SAP/Maximo/CMMS integration boundary.
    A real adapter implements create_order/update_order against the live system."""

    name = "mock_cmms"

    def create_order(self, work_order: dict) -> dict:
        return {"external_ref": f"CMMS-{work_order['id']}", "status": "accepted",
                "note": "mock adapter — replace with SAP/Maximo adapter for live integration"}

    def update_order(self, external_ref: str, status: str) -> dict:
        return {"external_ref": external_ref, "status": status}


@dataclass
class WorkOrder:
    id: str
    equipment_tag: str
    action: str
    parts: str
    priority: str
    schedule: str
    reason: str
    status: str = "pending_approval"   # pending_approval → approved → executed | rejected
    created_at: float = field(default_factory=time.time)
    audit: list = field(default_factory=list)
    external_ref: str | None = None


class WorkflowEngine:
    def __init__(self, adapter=None, notifier=None, memory=None):
        self.adapter = adapter or MockCMMSAdapter()
        self.notifier = notifier          # callable(title, message, severity) -> dict
        self.memory = memory              # MemoryLayer (optional)
        self._orders: dict[str, WorkOrder] = {}
        self._seq = itertools.count(1)

    # ---- lifecycle ----
    def create_from_assessment(self, assessment: dict) -> dict:
        """Draft a work order from a Reasoning Engine assessment. Held for
        human approval — nothing executes yet."""
        tag = assessment.get("equipment_tag", "unknown")
        risk = (assessment.get("risk") or {})
        wo = WorkOrder(
            id=f"WO-{next(self._seq):04d}",
            equipment_tag=tag,
            action=assessment.get("recommendation", "inspection"),
            parts=assessment.get("recommended_part", "as diagnosed"),
            priority="High" if risk.get("level") == "high" else "Medium",
            schedule=f"within {assessment.get('hours_to_elevated_risk') or 24} h",
            reason=assessment.get("narrative", "")[:400],
        )
        wo.audit.append({"event": "created", "ts": time.time(),
                         "detail": f"auto-drafted from reasoning assessment (risk={risk.get('risk')})"})
        self._orders[wo.id] = wo
        return self._view(wo)

    def approve(self, order_id: str, approver: str = "engineer") -> dict:
        """Human approval → execute every step with an audit entry per step."""
        wo = self._require(order_id)
        if wo.status != "pending_approval":
            return {"error": f"{order_id} is {wo.status}, not pending_approval"}
        wo.status = "approved"
        wo.audit.append({"event": "approved", "ts": time.time(), "detail": f"by {approver}"})
        return self._execute(wo)

    def reject(self, order_id: str, approver: str = "engineer", reason: str = "") -> dict:
        wo = self._require(order_id)
        wo.status = "rejected"
        wo.audit.append({"event": "rejected", "ts": time.time(),
                         "detail": f"by {approver}: {reason or 'no reason given'}"})
        return self._view(wo)

    def _execute(self, wo: WorkOrder) -> dict:
        # 1. Notify the maintenance lead.
        if self.notifier:
            note = self.notifier(f"Work order {wo.id} approved",
                                 f"{wo.action} · parts: {wo.parts} · {wo.schedule}", "high")
            wo.audit.append({"event": "notified", "ts": time.time(),
                             "detail": f"recipients={note.get('recipients')}"})
        # 2. Reserve spare parts (internal inventory intent).
        wo.audit.append({"event": "parts_reserved", "ts": time.time(), "detail": wo.parts})
        # 3. External CMMS/SAP handoff via the adapter.
        ext = self.adapter.create_order(self._view(wo))
        wo.external_ref = ext.get("external_ref")
        wo.audit.append({"event": "cmms_handoff", "ts": time.time(),
                         "detail": f"{self.adapter.name} → {wo.external_ref}"})
        # 4. Organizational memory.
        if self.memory is not None:
            self.memory.commit_long_term({"type": "work_order", "id": wo.id,
                                          "equipment_tag": wo.equipment_tag, "action": wo.action})
            self.memory.log_incident({"equipment_tag": wo.equipment_tag,
                                      "level": wo.priority.lower(), "work_order": wo.id,
                                      "risk": None, "factors": [wo.action]})
        wo.status = "executed"
        wo.audit.append({"event": "executed", "ts": time.time(), "detail": "all steps complete"})
        return self._view(wo)

    # ---- queries ----
    def list_orders(self, status: str | None = None) -> list[dict]:
        return [self._view(w) for w in self._orders.values()
                if status is None or w.status == status]

    def get(self, order_id: str) -> dict:
        return self._view(self._require(order_id))

    def _require(self, order_id: str) -> WorkOrder:
        if order_id not in self._orders:
            raise KeyError(f"No such work order: {order_id}")
        return self._orders[order_id]

    @staticmethod
    def _view(wo: WorkOrder) -> dict:
        return {"id": wo.id, "equipment_tag": wo.equipment_tag, "action": wo.action,
                "parts": wo.parts, "priority": wo.priority, "schedule": wo.schedule,
                "reason": wo.reason, "status": wo.status, "external_ref": wo.external_ref,
                "audit": wo.audit}
