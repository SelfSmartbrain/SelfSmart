'''search_engine.py

Provides retrieval of relevant memories (working, episodic, semantic, procedural) for the ReasoningEngine.
Uses simple keyword matching and optional vector similarity via the SemanticMemory embeddings.
''' 

from typing import List, Dict, Any
from ..memory.working_memory import WorkingMemory
from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.procedural_memory import ProceduralMemory

class SearchEngine:
    def __init__(self, db_session, working_mem: WorkingMemory, semantic_mem: SemanticMemory):
        self.db = db_session
        self.working_mem = working_mem
        self.semantic_mem = semantic_mem

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top‑k relevant items for a query.
        
        Currently combines:
        * Working memory (exact key match).
        * Semantic memory vector similarity (stub: returns empty list).
        * Episodic memory simple text search on outcome field.
        """
        results: List[Dict[str, Any]] = []
        # Working memory exact matches
        wm_val = self.working_mem.get(query)
        if wm_val is not None:
            results.append({"source": "working_memory", "value": wm_val})
        # Episodic memory simple LIKE search
        eps = (
            self.db.query(EpisodicMemory)
            .filter(EpisodicMemory.outcome.ilike(f"%{query}%"))
            .limit(top_k)
            .all()
        )
        for e in eps:
            results.append({"source": "episodic_memory", "outcome": e.outcome, "id": e.id})
        # Semantic memory vector search
        semantic_results = self.semantic_mem.search(query, top_k=top_k)
        for sr in semantic_results:
            results.append({"source": "semantic_memory", "content": sr.content, "score": sr.score})
        return results
