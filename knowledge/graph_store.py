"""
In-memory knowledge graph, built with networkx. This is the concrete
implementation behind PS8's "Knowledge Graph" requirement -- it satisfies
the interface (add entities, link them, query relationships) without
needing Neo4j running, so the pipeline is demoable with zero infra setup.

Swap for a real Neo4j-backed store later by reimplementing this same
interface (add_entity, add_relationship, entities_in_document,
co_occurring_entities) against Cypher queries -- callers won't need to
change.
"""

from __future__ import annotations

import json

import networkx as nx


class KnowledgeGraph:
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()

    def add_entity(self, entity_type: str, value: str, source_doc: str) -> str:
        """Add (or reuse) a node for this entity, linked to its source document.
        Returns the node id. Same (type, value) pair reuses the same node --
        this is what gives us cross-document linkage (PS8's 'knowledge graph
        linkage completeness' evaluation criterion)."""
        node_id = f"{entity_type}:{value}"
        if node_id not in self.graph:
            self.graph.add_node(node_id, entity_type=entity_type, value=value, source_docs=set())
        self.graph.nodes[node_id]["source_docs"].add(source_doc)
        return node_id

    def add_relationship(self, node_a: str, node_b: str, relation: str) -> None:
        self.graph.add_edge(node_a, node_b, relation=relation)

    def entities_in_document(self, source_doc: str) -> list[dict]:
        return [
            {"id": n, **{k: v for k, v in d.items() if k != "source_docs"}}
            for n, d in self.graph.nodes(data=True)
            if source_doc in d.get("source_docs", set())
        ]

    def find_entities(self, entity_type: str | None = None, value_contains: str | None = None) -> list[dict]:
        """Query nodes by type and/or a case-insensitive substring of their value.
        Used by MaintenanceAgent (find an equipment tag), ComplianceAgent
        (find regulatory references), and LessonsLearnedAgent (scan incidents)."""
        needle = value_contains.lower() if value_contains else None
        out = []
        for n, d in self.graph.nodes(data=True):
            if entity_type and d.get("entity_type") != entity_type:
                continue
            if needle and needle not in d.get("value", "").lower():
                continue
            out.append({
                "id": n,
                "entity_type": d["entity_type"],
                "value": d["value"],
                "source_docs": list(d.get("source_docs", set())),
            })
        return out

    def related_entities(self, node_id: str) -> list[dict]:
        """Entities linked to node_id by any relationship (co-occurrence, etc.).
        This is how MaintenanceAgent pulls an equipment tag's associated
        parameters/dates/personnel, and how LessonsLearnedAgent walks patterns."""
        if node_id not in self.graph:
            return []
        neighbors: dict[str, dict] = {}
        for _, nbr, d in self.graph.out_edges(node_id, data=True):
            neighbors.setdefault(nbr, {"relations": set()})["relations"].add(d.get("relation"))
        for nbr, _, d in self.graph.in_edges(node_id, data=True):
            neighbors.setdefault(nbr, {"relations": set()})["relations"].add(d.get("relation"))
        out = []
        for nbr, info in neighbors.items():
            nd = self.graph.nodes[nbr]
            out.append({
                "id": nbr,
                "entity_type": nd.get("entity_type"),
                "value": nd.get("value"),
                "relations": [r for r in info["relations"] if r],
                "source_docs": list(nd.get("source_docs", set())),
            })
        return out

    def all_entities(self) -> list[dict]:
        return [
            {"id": n, "entity_type": d["entity_type"], "value": d["value"],
             "source_docs": list(d.get("source_docs", set()))}
            for n, d in self.graph.nodes(data=True)
        ]

    def cross_document_entities(self) -> list[dict]:
        """Entities that appear in more than one source document -- the
        direct evidence for 'knowledge graph linkage completeness.'"""
        return [
            {"id": n, "value": d["value"], "entity_type": d["entity_type"],
             "source_docs": list(d["source_docs"])}
            for n, d in self.graph.nodes(data=True)
            if len(d.get("source_docs", set())) > 1
        ]

    def stats(self) -> dict:
        return {
            "total_entities": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "cross_document_entities": len(self.cross_document_entities()),
        }

    def save(self, path: str) -> None:
        data = {
            "nodes": [
                {"id": n, "entity_type": d["entity_type"], "value": d["value"],
                 "source_docs": list(d["source_docs"])}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "relation": d.get("relation")}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
