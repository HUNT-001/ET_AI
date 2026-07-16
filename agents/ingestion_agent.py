"""
IngestionAgent -- "Universal Document Ingestion & Knowledge Graph Agent"
(PS8: AI for Industrial Knowledge Intelligence)

Processes PDFs (text-native; scanned/OCR path not yet implemented -- see
knowledge/pdf_extract.py TODO), extracts entities, and writes them into
the shared knowledge graph + vector store that KnowledgeAgent queries.

REAL implementation as of this version -- not a stub. Pass a real file
path in request.payload["path"] to ingest it.
"""

from agents.base import AgentRequest, AgentResponse, BaseAgent
from knowledge.pipeline import ingest_pdf
from knowledge.store import knowledge_graph, vector_store

# Entity types called out explicitly in the PS8 brief.
ENTITY_TYPES = [
    "equipment_tag", "process_parameter", "regulatory_reference", "personnel", "date",
]

SUPPORTED_SOURCE_TYPES = [
    "pdf", "pid_drawing", "scanned_form", "spreadsheet", "email_archive",
]


class IngestionAgent(BaseAgent):
    name = "ingestion"
    description = (
        "Universal Document Ingestion & Knowledge Graph Agent -- processes "
        "PDFs, extracts equipment tags, process parameters, regulatory "
        "references, personnel, and dates; writes a unified, auto-updating "
        "knowledge graph and vector index."
    )
    tools: list[str] = ["pdfplumber", "entity_extraction", "networkx_graph", "chromadb"]

    def run(self, request: AgentRequest) -> AgentResponse:
        path = request.payload.get("path")
        if not path:
            return AgentResponse(
                agent_name=self.name,
                result=None,
                confidence=0.0,
                notes="No 'path' provided in payload -- pass {'path': '/path/to/doc.pdf'}.",
            )

        try:
            result = ingest_pdf(path, graph=knowledge_graph, vector_store=vector_store)
        except ValueError as e:
            # e.g. scanned PDF with no extractable text -- OCR not yet wired
            return AgentResponse(
                agent_name=self.name, result=None, confidence=0.0, notes=str(e),
            )

        return AgentResponse(
            agent_name=self.name,
            result={
                "source_doc": result.source_doc,
                "pages_ingested": result.num_pages,
                "chunks_created": result.num_chunks,
                "entities_found": result.entities_found,
            },
            confidence=1.0 if result.num_chunks > 0 else 0.0,
            notes="Real ingestion — PDF text extraction, entity extraction, graph + vector write all executed.",
        )
