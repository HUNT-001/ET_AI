"""
End-to-end ingestion pipeline: PDF -> text -> structure-aware chunks ->
entities -> typed knowledge graph + hybrid vector index.

A single shared KnowledgeGraph + VectorStore instance is used across the
process so KnowledgeAgent queries see what IngestionAgent has ingested.
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.pdf_extract import extract_pdf_text, chunk_structured
from knowledge.entity_extraction import extract_entities
from knowledge.graph_store import KnowledgeGraph
from knowledge.vector_store import VectorStore
from knowledge.ontology import map_symptoms
from knowledge.temporal import temporal_graph

# Which relationship an equipment tag has to each co-occurring entity type.
# This turns the graph from generic co-occurrence into a typed industrial graph.
_RELATION_BY_TYPE = {
    "process_parameter": "has_parameter",
    "date": "inspected_on",
    "regulatory_reference": "governed_by",
    "personnel": "involves",
    "equipment_tag": "co_located_with",
}


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
    chunk_meta: list[dict] = []
    entity_counts: dict[str, int] = {}

    for page in doc.pages:
        if not page.text.strip():
            continue
        for piece in chunk_structured(page.text):
            chunk = piece["text"]
            section = piece.get("section") or "General"
            all_chunks.append(chunk)
            chunk_pages.append(page.page_number)
            chunk_meta.append({"section": section})

            # Extract entities and add typed relationships anchored on each
            # equipment tag in the chunk.
            nodes: list[tuple[str, str]] = []
            vals: dict[str, list[str]] = {}
            for entity in extract_entities(chunk):
                node_id = graph.add_entity(entity.entity_type, entity.value, source_doc=path)
                nodes.append((entity.entity_type, node_id))
                vals.setdefault(entity.entity_type, []).append(entity.value)
                entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1

            equipment = [nid for etype, nid in nodes if etype == "equipment_tag"]
            for eq in equipment:
                for etype, nid in nodes:
                    if nid == eq:
                        continue
                    graph.add_relationship(eq, nid, relation=_RELATION_BY_TYPE.get(etype, "related_to"))

            # Temporal layer: record each equipment tag's dated observations, so
            # the platform can reason over time ("what changed", recurrence).
            symptoms = map_symptoms(chunk) or ["observation"]
            for tag in vals.get("equipment_tag", []):
                for date in vals.get("date", []):
                    for sym in symptoms:
                        temporal_graph.record(tag, sym, chunk.strip()[:140], date, source=path)

    if all_chunks:
        vector_store.add_chunks(all_chunks, source_doc=path, page_numbers=chunk_pages,
                                extra_metadata=chunk_meta)

    return IngestionResult(
        source_doc=path,
        num_pages=len(doc.pages),
        num_chunks=len(all_chunks),
        entities_found=entity_counts,
    )
