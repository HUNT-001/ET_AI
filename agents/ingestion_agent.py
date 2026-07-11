"""
IngestionAgent — "Universal Document Ingestion & Knowledge Graph Agent"
(PS8: AI for Industrial Knowledge Intelligence)

Processes PDFs, P&IDs, scanned forms, spreadsheets, and email archives.
Extracts entities and builds/updates a unified knowledge graph that
maintains relationships across document types as new records arrive.

This is the entry point for every other PS8 agent — Knowledge, Maintenance,
Compliance, and Lessons-Learned all query the graph/index this agent builds.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent

# Entity types called out explicitly in the PS8 brief. Extraction should
# tag spans with one of these categories so downstream agents (Compliance,
# Maintenance) can query the graph by entity type.
ENTITY_TYPES = [
    "equipment_tag",       # e.g. "P-101A", "V-204"
    "process_parameter",   # e.g. "operating pressure", "flow rate"
    "regulatory_reference", # e.g. "OISD-STD-118", "Factory Act Sec. 21"
    "personnel",           # names/roles referenced in logs, sign-offs
    "date",                 # inspection dates, permit validity, incident dates
]

SUPPORTED_SOURCE_TYPES = [
    "pdf", "pid_drawing", "scanned_form", "spreadsheet", "email_archive",
]


class IngestionAgent(BaseAgent):
    name = "ingestion"
    description = (
        "Universal Document Ingestion & Knowledge Graph Agent — processes "
        "PDFs, P&IDs, scanned forms, spreadsheets, and email archives; "
        "extracts equipment tags, process parameters, regulatory references, "
        "personnel, and dates; builds a unified, auto-updating knowledge graph."
    )
    tools: list[str] = ["ocr", "paddleocr", "entity_extraction", "neo4j_write", "vector_upsert"]

    def run(self, request: AgentRequest) -> AgentResponse:
        # TODO: real pipeline — OCR (PaddleOCR/EasyOCR) -> layout/entity
        # extraction (spaCy/LLM-based NER tuned on ENTITY_TYPES) -> write
        # nodes/edges to Neo4j -> upsert embeddings to Chroma/Qdrant.
        return AgentResponse(
            agent_name=self.name,
            result=f"[stub] would ingest document(s) for task='{request.task}'",
            confidence=0.0,
            notes="Stub — wire to OCR + entity extraction + Neo4j + vector DB.",
        )
