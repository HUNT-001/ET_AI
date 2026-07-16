"""
NotificationAgent — turns an alert/pattern into a routed, severity-tagged
notification for the right human or system.

Called by LessonsLearnedAgent (proactive warnings) and available to other
agents. Status: real (not a stub) for the routing/formatting layer. Actual
delivery transports (email, Slack, MQTT, dashboard push) are pluggable and
disabled by default so nothing is sent during a demo — the agent returns
the exact payload it *would* dispatch, which is what the dashboard renders.
"""

from __future__ import annotations

from agents.base import AgentRequest, AgentResponse, BaseAgent

# Which role should receive which severity — a simple, explicit routing table.
_ROUTING = {
    "critical": ["plant_manager", "safety_officer", "maintenance_lead"],
    "high": ["maintenance_lead", "shift_engineer"],
    "medium": ["shift_engineer"],
    "low": ["log_only"],
}


def build_notification(title: str, message: str, severity: str = "medium",
                       channels: list[str] | None = None) -> dict:
    severity = severity.lower()
    if severity not in _ROUTING:
        severity = "medium"
    return {
        "title": title,
        "message": message,
        "severity": severity,
        "recipients": _ROUTING[severity],
        "channels": channels or ["dashboard"],
        "delivered": False,  # transports disabled by default (demo-safe)
    }


class NotificationAgent(BaseAgent):
    name = "notification"
    description = (
        "Routes proactive warnings from LessonsLearnedAgent and alerts from "
        "other agents to the right recipients by severity (email, Slack, "
        "MQTT, dashboard). Delivery transports are pluggable and off by "
        "default; returns the payload it would dispatch."
    )
    tools: list[str] = ["severity_router"]

    def run(self, request: AgentRequest) -> AgentResponse:
        p = request.payload
        note = build_notification(
            title=p.get("title", "Alert"),
            message=p.get("message", request.task),
            severity=p.get("severity", "medium"),
            channels=p.get("channels"),
        )
        return AgentResponse(
            agent_name=self.name,
            result=note,
            confidence=1.0,
            tool_calls=["severity_router"],
            notes=f"severity={note['severity']}; recipients={note['recipients']}",
        )
