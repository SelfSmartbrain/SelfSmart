from __future__ import annotations

import networkx as nx
from typing import Dict, Any, List
from src.config.logging import get_logger

logger = get_logger(__name__)

class DependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, mapping_data: Dict[str, Any]) -> None:
        logger.info("Building dependency graph...")
        
        for node in mapping_data.get("nodes", []):
            self.graph.add_node(node["id"], **node)
            
        for edge in mapping_data.get("edges", []):
            self.graph.add_edge(edge["source"], edge["target"], type=edge["type"])
            
        logger.info(f"Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def get_components_by_type(self, component_type: str) -> List[Dict[str, Any]]:
        return [
            data for node, data in self.graph.nodes(data=True)
            if data.get("type") == component_type
        ]
        
    def get_dependencies(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(self.graph.successors(node_id))
        
    def get_dependents(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(self.graph.predecessors(node_id))

    def analyze_centrality(self) -> Dict[str, float]:
        if self.graph.number_of_nodes() == 0:
            return {}
        return nx.degree_centrality(self.graph)
