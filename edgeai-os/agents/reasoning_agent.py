"""
ReasoningAgent — General-purpose LLM/SLM reasoning over retrieved context; the closest thing to a 'chatbot', but scoped and tool-using.

This is a scaffold stub: it implements the BaseAgent contract with a
placeholder `run()` so the Orchestrator and API can be wired up and tested
end-to-end before the real model/tool integration is built.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent


class ReasoningAgent(BaseAgent):
    name = "reasoning"
    description = "Shared LLM/SLM reasoning engine used internally by KnowledgeAgent (Expert Knowledge Copilot) and MaintenanceAgent (RCA) — not called directly by users."
    tools: list[str] = []  # TODO: e.g. ["yolov11", "vector_search", "neo4j_query"]

    def run(self, request: AgentRequest) -> AgentResponse:
        # TODO: replace with real model/tool calls.
        return AgentResponse(
            agent_name=self.name,
            result=f"[stub] {self.name} received task='{request.task}'",
            confidence=0.0,
            notes="Stub response — implement real logic in agents/reasoning_agent.py",
        )
