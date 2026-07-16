"""
End-to-end ingestion pipeline: PDF -> text -> chunks -> entities ->
knowledge graph + vector store. This is what IngestionAgent calls.

A single shared KnowledgeGraph + VectorStore instance is used across the
process so KnowledgeAgent queries see what IngestionAgent has ingested --
see knowledge/store.py for the shared singletons.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.pdf_extract import extract_pdf_text, chunk_text
from knowledge.entity_extraction import extract_entities
from knowledge.graph_store import KnowledgeGraph
from knowledge.vector_store import VectorStore


@dataclass
class IngestionResult:
    source_doc: str
    num_pages: int
    num_chunks: int
    entities_found: dict[str, int]  # entity_type -> count


def ingest_pdf(path: str, graph: KnowledgeGraph, vector_store: VectorStore) -> IngestionResult:
    doc = extract_pdf_text(path)

    all_chunks: list[str] = []
    chunk_pages: list[int] = []
    entity_counts: dict[str, int] = {}

    for page in doc.pages:
        if not page.text.strip():
            continue
        page_chunks = chunk_text(page.text)
        for chunk in page_chunks:
            all_chunks.append(chunk)
            chunk_pages.append(page.page_number)

            # Extract entities, add each to the graph, and link entities that
            # co-occur in the same chunk. Anchoring co-occurrence edges on the
            # equipment tag(s) in a chunk is what lets MaintenanceAgent pull an
            # asset's associated parameters/dates/personnel, and gives the
            # knowledge graph real relationships (not just isolated nodes).
            chunk_nodes: list[tuple[str, str]] = []  # (entity_type, node_id)
            for entity in extract_entities(chunk):
                node_id = graph.add_entity(entity.entity_type, entity.value, source_doc=path)
                chunk_nodes.append((entity.entity_type, node_id))
                entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1

            equipment = [nid for etype, nid in chunk_nodes if etype == "equipment_tag"]
            for eq in equipment:
                for etype, nid in chunk_nodes:
                    if nid == eq:
                        continue
                    graph.add_relationship(eq, nid, relation="co_occurs_with")

    if all_chunks:
        vector_store.add_chunks(all_chunks, source_doc=path, page_numbers=chunk_pages)

    return IngestionResult(
        source_doc=path,
        num_pages=len(doc.pages),
        num_chunks=len(all_chunks),
        entities_found=entity_counts,
    )
