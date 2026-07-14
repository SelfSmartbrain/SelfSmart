'''search_engine.py
 
Provides retrieval of relevant memories (working, episodic, semantic, procedural) for the ReasoningEngine.
Uses simple keyword matching and optional vector similarity via the SemanticMemory embeddings.
''' 

from typing import List, Dict, Any
import logging
from ..memory.working_memory import WorkingMemory
from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.procedural_memory import ProceduralMemory

# Lazy-load the sentence transformer model to avoid importing at module level if not used
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

logger = logging.getLogger(__name__)

class SearchEngine:
    def __init__(self, db_session, working_mem: WorkingMemory, semantic_mem: SemanticMemory):
        self.db = db_session
        self.working_mem = working_mem
        self.semantic_mem = semantic_mem

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top‑k relevant items for a query.
        
        Currently combines:
        * Working memory (exact key match).
        * Semantic memory vector similarity (now using sentence-transformers).
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
        if self.semantic_mem is not None:
            try:
                # Get the vector for the query
                query_vector = _get_embedding_model().encode(query).tolist()
                semantic_results = self.semantic_mem.similarity_search(query_vector, top_k=top_k)
                for sr in semantic_results:
                    results.append({"source": "semantic_memory", "content": sr.content, "score": sr.score})
            except Exception as e:
                logger.warning(f"Semantic memory search failed: {e}")
        return results