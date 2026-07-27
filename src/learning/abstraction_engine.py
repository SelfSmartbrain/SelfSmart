"""abstraction_engine.py

Engine that abstracts low‑level episodic events into higher‑level concepts.
Uses sentence embeddings to group similar outcomes and generate abstract representations.
"""

from typing import List, Dict
import logging
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


class AbstractionEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.model = None
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                logger.info("AbstractionEngine: SentenceTransformer model loaded")
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer model: {e}")
                self.model = None
        else:
            logger.warning("SentenceTransformer not available, using stub mode")

    def abstract(self, episodes: List[EpisodicMemory]) -> List[Dict]:
        """Create abstract representations from a list of episodes.
        Groups episodes by semantic similarity of their outcome field and returns a summary for each group.
        """
        if self.model is None or not episodes:
            # Fallback to original simple method
            groups = {}
            for ep in episodes:
                key = (ep.outcome or "").split()[0] if ep.outcome else "unknown"
                groups.setdefault(key, []).append(ep)
            return [{"topic": k, "count": len(v)} for k, v in groups.items()]

        try:
            # Filter out episodes with empty or None outcome
            valid_episodes = [
                ep
                for ep in episodes
                if ep.outcome and isinstance(ep.outcome, str) and ep.outcome.strip()
            ]
            if not valid_episodes:
                return [{"topic": "no_valid_outcomes", "count": len(episodes)}]

            outcomes = [ep.outcome for ep in valid_episodes]
            # Compute embeddings
            embeddings = self.model.encode(outcomes, convert_to_tensor=True)
            # Compute cosine similarity matrix
            similarity_matrix = cos_sim(embeddings, embeddings)

            # Simple greedy clustering: sort by similarity to first element? We'll do a basic threshold-based clustering.
            # We'll assign each episode to the first cluster whose centroid is similar enough.
            # For simplicity, we'll use the first element of each cluster as the centroid.
            clusters: List[List[int]] = []  # list of lists of indices in valid_episodes
            used = [False] * len(valid_episodes)
            similarity_threshold = 0.7  # adjustable

            for i in range(len(valid_episodes)):
                if used[i]:
                    continue
                # Start a new cluster with i
                clusters.append([i])
                used[i] = True
                for j in range(i + 1, len(valid_episodes)):
                    if not used[j] and similarity_matrix[i][j].item() > similarity_threshold:
                        clusters[-1].append(j)
                        used[j] = True

            # Build abstracts
            abstracts = []
            for cluster_indices in clusters:
                # Get the outcomes in this cluster
                cluster_outcomes = [outcomes[idx] for idx in cluster_indices]
                # Use the first outcome as a representative, or we could combine them
                representative = cluster_outcomes[0]
                # Create a simple summary: we can count and maybe take a common phrase?
                # For now, we just return the representative and count.
                abstracts.append(
                    {
                        "topic": (
                            representative[:50] + "..."
                            if len(representative) > 50
                            else representative
                        ),
                        "count": len(cluster_indices),
                        "examples": cluster_outcomes[:3],  # include up to 3 examples
                    }
                )
            return abstracts
        except Exception as e:
            logger.error(f"AbstractionEngine error: {e}")
            # Fallback to original method
            groups = {}
            for ep in episodes:
                key = (ep.outcome or "").split()[0] if ep.outcome else "unknown"
                groups.setdefault(key, []).append(ep)
            return [{"topic": k, "count": len(v)} for k, v in groups.items()]
