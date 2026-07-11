'''causal_graph_engine.py

Extends the existing Neo4j causal graph with temporal edges and versioning.
Provides methods to add causal relationships and query counterfactual paths.
''' 

from neo4j import GraphDatabase
from typing import List, Dict, Any

class CausalGraphEngine:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_causal_edge(self, src: str, dst: str, relation: str, timestamp: str = None, properties: Dict[str, Any] = None):
        """Create a causal edge between two entities.
        
        `src` and `dst` are node identifiers; `relation` is the type of causal link.
        Optional `timestamp` adds temporal ordering.
        """
        props = properties or {}
        if timestamp:
            props["timestamp"] = timestamp
        with self.driver.session() as session:
            cypher = (
                f"MERGE (a:Entity {{id: $src}}) "
                f"MERGE (b:Entity {{id: $dst}}) "
                f"MERGE (a)-[r:{relation} $props]->(b)"
            )
            session.run(cypher, src=src, dst=dst, props=props)

    def query_path(self, start: str, end: str, max_hops: int = 5) -> List[Dict[str, Any]]:
        """Return possible causal paths between `start` and `end` up to `max_hops`.
        """
        with self.driver.session() as session:
            cypher = (
                "MATCH path = (a:Entity {id: $start})-[:*..$max_hops]->(b:Entity {id: $end}) "
                "RETURN path"
            )
            result = session.run(cypher, start=start, end=end, max_hops=max_hops)
            paths = []
            for record in result:
                paths.append(record["path"].nodes)
            return paths

    def __repr__(self):
        return "CausalGraphEngine()"
