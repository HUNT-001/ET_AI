"""
VisionAgent — P&ID parsing and engineering-drawing digitisation (PS8's
"Computer Vision" suggested technology).

REAL implementation (OpenCV + optional Tesseract OCR — see
knowledge/pid_vision.py): detects equipment symbols (circles/rectangles) and
piping lines, OCRs equipment tags, and writes the tags into the shared
knowledge graph so drawing entities link with document entities (cross-modal
linkage). Honest scope: tuned for clean digital P&IDs; legacy scans degrade.
"""

from __future__ import annotations

from agents.base import AgentRequest, AgentResponse, BaseAgent


class VisionAgent(BaseAgent):
    name = "vision"
    description = (
        "P&ID / engineering-drawing digitisation — OpenCV symbol + piping-line "
        "detection with OCR tag extraction; detected equipment tags feed the "
        "shared knowledge graph for cross-modal linkage."
    )
    tools: list[str] = ["opencv_symbol_detector", "hough_lines", "tesseract_ocr", "graph_write"]

    def run(self, request: AgentRequest) -> AgentResponse:
        path = request.payload.get("path")
        if not path:
            return AgentResponse(agent_name=self.name, result=None, confidence=0.0,
                                 notes="No 'path' in payload — pass {'path': '/path/to/drawing.png'}.")
        try:
            from knowledge.pid_vision import ingest_pid
            from knowledge.store import knowledge_graph

            result = ingest_pid(path, knowledge_graph)
        except ImportError as e:
            return AgentResponse(agent_name=self.name, result=None, confidence=0.0,
                                 notes=f"OpenCV not installed ({e}). pip install opencv-python-headless.")
        except ValueError as e:
            return AgentResponse(agent_name=self.name, result=None, confidence=0.0, notes=str(e))

        tags = result["equipment_tags"]
        conf = 0.9 if tags else (0.5 if result["symbols"]["circles"] + result["symbols"]["rectangles"] > 0 else 0.2)
        return AgentResponse(
            agent_name=self.name,
            result=result,
            confidence=conf,
            tool_calls=["opencv_symbol_detector", "hough_lines"] + (["tesseract_ocr"] if result["ocr_used"] else []),
            notes=result["summary"],
        )
