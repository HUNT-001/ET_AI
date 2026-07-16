"""
VisionAgent — supports the Universal Document Ingestion pipeline
(PS8: AI for Industrial Knowledge Intelligence)

PS8's suggested technologies explicitly include "Computer Vision (P&ID
parsing, drawing digitisation)". This agent handles the visual/structural
side of ingestion — parsing piping & instrumentation diagrams and scanned
engineering drawings — while IngestionAgent handles text-centric OCR and
entity extraction. IngestionAgent calls this agent for drawing-type inputs.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent


class VisionAgent(BaseAgent):
    name = "vision"
    description = (
        "P&ID parsing and engineering drawing digitisation — extracts "
        "equipment symbols, tag numbers, and connectivity from piping & "
        "instrumentation diagrams and scanned drawings for the ingestion "
        "pipeline."
    )
    tools: list[str] = ["pid_symbol_detector", "layout_parser", "ocr"]

    def run(self, request: AgentRequest) -> AgentResponse:
        # TODO: real pipeline — symbol detection (fine-tuned YOLO on P&ID
        # symbol library) + line/connectivity tracing + tag-number OCR ->
        # structured output handed to IngestionAgent for graph construction.
        return AgentResponse(
            agent_name=self.name,
            result=f"[stub] would parse drawing/P&ID for task='{request.task}'",
            confidence=0.0,
            notes="Stub — wire to P&ID symbol detection + OCR.",
        )
