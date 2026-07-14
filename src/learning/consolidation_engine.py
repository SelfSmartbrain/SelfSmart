'''consolidation_engine.py

Engine that merges duplicate episodic memories and creates unified representations.
Uses sentence embeddings to detect semantically similar episodes and merges them.
'''

from typing import List
import logging
from sqlalchemy.orm import Session
from ..memory.episodic_memory import EpisodicMemory

try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.util import cos_sim
    import torch
except ImportError:
    # Fallback if sentence-transformers is not available
    SentenceTransformer = None
    cos_sim = None
    torch = None

logger = logging.getLogger(__name__)

class ConsolidationEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.model = None
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                logger.info("ConsolidationEngine: SentenceTransformer model loaded")
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer model: {e}")
                self.model = None
        else:
            logger.warning("SentenceTransformer not available, using stub mode")

    def merge_duplicates(self, similarity_threshold: float = 0.85) -> None:
        """Detect and merge duplicate episodes based on semantic similarity of outcomes."""
        if self.model is None:
            logger.warning("ConsolidationEngine: skipping duplicate merge (model not available)")
            print("ConsolidationEngine: merging duplicates (stub)")
            return

        try:
            # Fetch all episodes with id and outcome
            episodes = self.db.query(EpisodicMemory.id, EpisodicMemory.outcome).all()
            if not episodes:
                logger.info("ConsolidationEngine: no episodes to process")
                return

            # Filter out episodes with empty or None outcome
            valid_episodes = [(eid, out) for eid, out in episodes if out and isinstance(out, str) and out.strip()]
            if len(valid_episodes) < 2:
                logger.info("ConsolidationEngine: insufficient valid episodes for comparison")
                return

            ids, outcomes = zip(*valid_episodes)
            # Compute embeddings
            embeddings = self.model.encode(outcomes, convert_to_tensor=True)
            # Compute cosine similarity matrix
            similarity_matrix = cos_sim(embeddings, embeddings)

            # Find duplicates using a greedy approach (each duplicate is assigned to the first similar episode)
            duplicate_ids = set()
            processed = [False] * len(ids)
            for i in range(len(ids)):
                if processed[i]:
                    continue
                # Mark current as processed (it will be the canonical)
                processed[i] = True
                for j in range(i + 1, len(ids)):
                    if not processed[j] and similarity_matrix[i][j].item() > similarity_threshold:
                        duplicate_ids.add(ids[j])
                        processed[j] = True

            if not duplicate_ids:
                logger.info("ConsolidationEngine: no duplicates found")
                return

            # Delete duplicate episodes
            deleted_count = 0
            for dup_id in duplicate_ids:
                duplicate = self.db.get(EpisodicMemory, dup_id)
                if duplicate:
                    self.db.delete(duplicate)
                    deleted_count += 1
                else:
                    logger.warning(f"ConsolidationEngine: duplicate ID {dup_id} not found")

            logger.info(f"ConsolidationEngine: merged {deleted_count} duplicate episodes")
            print(f"ConsolidationEngine: merged {deleted_count} duplicate episodes")

        except Exception as e:
            logger.error(f"ConsolidationError: {e}")
            print(f"ConsolidationEngine: error during duplicate merge: {e}")

    def run(self) -> None:
        """Run the consolidation pipeline."""
        self.merge_duplicates()
        # Future: call abstraction and forgetting engines
        logger.info("ConsolidationEngine: pipeline completed")