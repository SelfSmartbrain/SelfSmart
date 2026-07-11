'''semantic_memory.py

Implements a semantic memory layer that stores concepts, facts, relationships, and theories.
It uses Neo4j for graph storage and Qdrant for vector embeddings to enable similarity search.
''' 

from typing import List, Dict, Any
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

class SemanticMemory:
    """Interface for storing and retrieving semantic knowledge.
    
    Nodes are stored in Neo4j; embeddings are stored in Qdrant for fast vector search.
    """

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = "semantic_embeddings"
        # Ensure collection exists
        if self.collection_name not in self.qdrant.get_collections().collections:
            self.qdrant.recreate_collection(
                collection_name=self.collection_name,
                vector_size=768,  # assume 768-dim embeddings
                distance="Cosine",
            )

    # ------- Graph operations (Neo4j) -------
    def create_node(self, label: str, properties: Dict[str, Any]) -> None:
        with self.driver.session() as session:
            cypher = f"CREATE (n:{label} $props)"
            session.run(cypher, props=properties)

    def create_relationship(self, src_id: int, dst_id: int, rel_type: str, props: Dict[str, Any] = None) -> None:
        with self.driver.session() as session:
            cypher = """
            MATCH (a), (b)
            WHERE id(a) = $src_id AND id(b) = $dst_id
            CREATE (a)-[r:%s $props]->(b)
            """ % rel_type
            session.run(cypher, src_id=src_id, dst_id=dst_id, props=props or {})

    # ------- Embedding operations (Qdrant) -------
    def upsert_embedding(self, entity_id: str, vector: List[float], payload: Dict[str, Any] = None) -> None:
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": entity_id,
                    "vector": vector,
                    "payload": payload or {},
                }
            ],
        )

    def similarity_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
        return [hit.payload for hit in results]

    def close(self):
        self.driver.close()
        self.qdrant.close()

    def __repr__(self) -> str:
        return f"SemanticMemory(neo4j={self.driver.uri})"
