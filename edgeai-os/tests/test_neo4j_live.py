"""
Live Neo4j integration test — runs the full graph interface against a real
Neo4j when one is reachable, and SKIPS cleanly when not (so CI and machines
without Neo4j stay green).

To exercise it live:
    docker run -d -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
    set NEO4J_URI=bolt://localhost:7687  NEO4J_USER=neo4j  NEO4J_PASSWORD=password
    pytest tests/test_neo4j_live.py -v
"""

import os

import pytest


def _neo4j_reachable():
    uri = os.environ.get("NEO4J_URI")
    if not uri:
        return False
    try:
        from neo4j import GraphDatabase

        drv = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USER", "neo4j"),
                                              os.environ.get("NEO4J_PASSWORD", "")))
        drv.verify_connectivity()
        drv.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _neo4j_reachable(),
                                reason="Neo4j not reachable (set NEO4J_URI/USER/PASSWORD and run a server)")


@pytest.fixture()
def graph():
    from knowledge.graph_store_neo4j import Neo4jKnowledgeGraph

    g = Neo4jKnowledgeGraph(os.environ["NEO4J_URI"], os.environ.get("NEO4J_USER", "neo4j"),
                            os.environ.get("NEO4J_PASSWORD", ""))
    # Clean slate for the test entities.
    with g._session() as s:
        s.run("MATCH (e:Entity) WHERE e.id STARTS WITH 'equipment_tag:TEST-' DETACH DELETE e")
    yield g
    with g._session() as s:
        s.run("MATCH (e:Entity) WHERE e.id STARTS WITH 'equipment_tag:TEST-' DETACH DELETE e")
    g.close()


def test_live_roundtrip(graph):
    a = graph.add_entity("equipment_tag", "TEST-101A", source_doc="doc1.pdf")
    graph.add_entity("equipment_tag", "TEST-101A", source_doc="doc2.pdf")  # same node, 2nd doc
    b = graph.add_entity("equipment_tag", "TEST-204", source_doc="doc1.pdf")
    graph.add_relationship(a, b, relation="co_located_with")

    found = graph.find_entities(entity_type="equipment_tag", value_contains="TEST-101A")
    assert found and sorted(found[0]["source_docs"]) == ["doc1.pdf", "doc2.pdf"]

    rel = graph.related_entities(a)
    assert any(r["value"] == "TEST-204" for r in rel)

    cross = [e for e in graph.cross_document_entities() if e["value"] == "TEST-101A"]
    assert cross, "same tag across two docs should be cross-document"

    stats = graph.stats()
    assert stats["total_entities"] >= 2
