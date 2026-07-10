"""
PlannerAgent — Breaks a high-level goal into an ordered sequence of agent calls (Planner -> Vision -> Sensor -> Risk -> Simulation -> Compliance -> Report, per Architecture.md).

This is a scaffold stub: it implements the BaseAgent contract with a
placeholder `run()` so the Orchestrator and API can be wired up and tested
end-to-end before the real model/tool integration is built.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent


class PlannerAgent(BaseAgent):
    name = "planner"
    description = "Breaks a high-level goal into an ordered sequence of the 5 PS8 primary agents (Ingestion -> Knowledge/Maintenance -> Compliance -> Lessons Learned -> Report)."
    tools: list[str] = []  # TODO: e.g. ["yolov11", "vector_search", "neo4j_query"]

    def run(self, request: AgentRequest) -> AgentResponse:
        # TODO: replace with real model/tool calls.
        return AgentResponse(
            agent_name=self.name,
            result=f"[stub] {self.name} received task='{request.task}'",
            confidence=0.0,
            notes="Stub response — implement real logic in agents/planner_agent.py",
        )
