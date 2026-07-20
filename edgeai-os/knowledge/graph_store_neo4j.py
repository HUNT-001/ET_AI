"""
Neo4j-backed knowledge graph — a drop-in replacement for the in-memory
`networkx` KnowledgeGraph (knowledge/graph_store.py). It implements the exact
same interface (add_entity, add_relationship, entities_in_document,
find_entities, related_entities, all_entities, cross_document_entities, stats,
save), so no agent or pipeline code changes — only `knowledge/store.py`'s
backend selection.

Enable it by setting EDGEAI_GRAPH=neo4j and NEO4J_URI / NEO4J_USER /
NEO4J_PASSWORD. Entities are keyed by `type:value` (same convention as the
in-memory store), so the same tag across documents resolves to one node —
preserving PS8's cross-document linkage semantics with real persistence.
"""

from __future__ import annotations


class Neo4jKnowledgeGraph:
    def __init__(self, uri: str, user: str, password: str, database: str | None = None):
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._ensure_schema()

    def _session(self):
        return self._driver.session(database=self._database) if self._database else self._driver.session()

    def _ensure_schema(self) -> None:
        with self._session() as s:
            s.run("CREATE CONSTRAINT entity_id IF NOT EXISTS "
                  "FOR (e:Entity) REQUIRE e.id IS UNIQUE")

    # ---- writes ----
    def add_entity(self, entity_type: str, value: str, source_doc: str) -> str:
        node_id = f"{entity_type}:{value}"
        with self._session() as s:
            s.run(
                "MERGE (e:Entity {id:$id}) "
                "ON CREATE SET e.entity_type=$t, e.value=$v, e.source_docs=[] "
                "SET e.source_docs = CASE WHEN $doc IN e.source_docs "
                "     THEN e.source_docs ELSE e.source_docs + $doc END",
                id=node_id, t=entity_type, v=value, doc=source_doc,
            )
        return node_id

    def add_relationship(self, node_a: str, node_b: str, relation: str) -> None:
        with self._session() as s:
            s.run(
                "MATCH (a:Entity {id:$a}), (b:Entity {id:$b}) "
                "MERGE (a)-[r:REL {relation:$rel}]->(b)",
                a=node_a, b=node_b, rel=relation,
            )

    # ---- reads ----
    def entities_in_document(self, source_doc: str) -> list[dict]:
        with self._session() as s:
            rows = s.run(
                "MATCH (e:Entity) WHERE $doc IN e.source_docs "
                "RETURN e.id AS id, e.entity_type AS entity_type, e.value AS value",
                doc=source_doc,
            )
            return [dict(r) for r in rows]

    def find_entities(self, entity_type: str | None = None, value_contains: str | None = None) -> list[dict]:
        clauses, params = [], {}
        if entity_type:
            clauses.append("e.entity_type=$t"); params["t"] = entity_type
        if value_contains:
            clauses.append("toLower(e.value) CONTAINS toLower($v)"); params["v"] = value_contains
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._session() as s:
            rows = s.run(
                f"MATCH (e:Entity) {where} "
                "RETURN e.id AS id, e.entity_type AS entity_type, e.value AS value, "
                "e.source_docs AS source_docs", **params,
            )
            return [{"id": r["id"], "entity_type": r["entity_type"], "value": r["value"],
                     "source_docs": r["source_docs"] or []} for r in rows]

    def related_entities(self, node_id: str) -> list[dict]:
        with self._session() as s:
            rows = s.run(
                "MATCH (e:Entity {id:$id})-[r:REL]-(n:Entity) "
                "RETURN n.id AS id, n.entity_type AS entity_type, n.value AS value, "
                "n.source_docs AS source_docs, collect(r.relation) AS relations",
                id=node_id,
            )
            return [{"id": r["id"], "entity_type": r["entity_type"], "value": r["value"],
                     "relations": [x for x in r["relations"] if x],
                     "source_docs": r["source_docs"] or []} for r in rows]

    def all_entities(self) -> list[dict]:
        with self._session() as s:
            rows = s.run("MATCH (e:Entity) RETURN e.id AS id, e.entity_type AS entity_type, "
                         "e.value AS value, e.source_docs AS source_docs")
            return [{"id": r["id"], "entity_type": r["entity_type"], "value": r["value"],
                     "source_docs": r["source_docs"] or []} for r in rows]

    def cross_document_entities(self) -> list[dict]:
        with self._session() as s:
            rows = s.run(
                "MATCH (e:Entity) WHERE size(e.source_docs) > 1 "
                "RETURN e.id AS id, e.value AS value, e.entity_type AS entity_type, "
                "e.source_docs AS source_docs")
            return [{"id": r["id"], "value": r["value"], "entity_type": r["entity_type"],
                     "source_docs": r["source_docs"] or []} for r in rows]

    def stats(self) -> dict:
        with self._session() as s:
            n = s.run("MATCH (e:Entity) RETURN count(e) AS c").single()["c"]
            m = s.run("MATCH ()-[r:REL]->() RETURN count(r) AS c").single()["c"]
            x = s.run("MATCH (e:Entity) WHERE size(e.source_docs) > 1 RETURN count(e) AS c").single()["c"]
        return {"total_entities": n, "total_relationships": m, "cross_document_entities": x}

    def save(self, path: str) -> None:
        # No-op: Neo4j is already persistent. Present for interface parity.
        return None

    def close(self) -> None:
        self._driver.close()
