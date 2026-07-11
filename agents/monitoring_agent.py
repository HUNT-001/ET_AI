"""
MonitoringAgent — Watches sensor/log streams for anomalies (Isolation Forest / Autoencoder) and raises alerts.

This is a scaffold stub: it implements the BaseAgent contract with a
placeholder `run()` so the Orchestrator and API can be wired up and tested
end-to-end before the real model/tool integration is built.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent


class MonitoringAgent(BaseAgent):
    name = "monitoring"
    description = "Watches for real-time condition/anomaly signals (Isolation Forest / Autoencoder) feeding MaintenanceAgent's live-condition context — supporting role."
    tools: list[str] = []  # TODO: e.g. ["yolov11", "vector_search", "neo4j_query"]

    def run(self, request: AgentRequest) -> AgentResponse:
        # TODO: replace with real model/tool calls.
        return AgentResponse(
            agent_name=self.name,
            result=f"[stub] {self.name} received task='{request.task}'",
            confidence=0.0,
            notes="Stub response — implement real logic in agents/monitoring_agent.py",
        )
