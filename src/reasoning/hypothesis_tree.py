'''hypothesis_tree.py

Simple data structure representing a tree of hypotheses (possible reasoning paths).
Each node holds a hypothesis string and a score. The `select_best` method returns the
path with the highest cumulative score.
''' 

from typing import List, Tuple

class HypothesisTree:
    def __init__(self, hypotheses: List[str]):
        # For simplicity, each hypothesis is a leaf node with score 1.0
        self.nodes: List[Tuple[str, float]] = [(h, 1.0) for h in hypotheses]

    def select_best(self) -> List[str]:
        """Return the hypotheses sorted by score (descending)."""
        # In a real implementation we'd traverse a tree; here we just return the list.
        sorted_nodes = sorted(self.nodes, key=lambda x: x[1], reverse=True)
        return [h for h, _ in sorted_nodes]

    def __repr__(self) -> str:
        return f"HypothesisTree(nodes={len(self.nodes)})"
