"""
Process-wide shared instances so IngestionAgent writes and KnowledgeAgent
reads from the same graph + vector store within one running backend.
Swap for real dependency injection once this moves past MVP.
"""

from knowledge.graph_store import KnowledgeGraph
from knowledge.vector_store import VectorStore

knowledge_graph = KnowledgeGraph()
vector_store = VectorStore()
