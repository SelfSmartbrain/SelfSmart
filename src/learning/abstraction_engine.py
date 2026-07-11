'''abstraction_engine.py

Engine that abstracts low‑level episodic events into higher‑level concepts.
Currently provides a stub `abstract` method that groups events by a simple keyword heuristic.
''' 

from typing import List, Dict
from ..memory.episodic_memory import EpisodicMemory

class AbstractionEngine:
    def __init__(self, db_session):
        self.db = db_session

    def abstract(self, episodes: List[EpisodicMemory]) -> List[Dict]:
        """Create abstract representations from a list of episodes.
        
        This placeholder groups episodes by the first word of the ``outcome`` field.
        """
        groups = {}
        for ep in episodes:
            key = (ep.outcome or "").split()[0] if ep.outcome else "unknown"
            groups.setdefault(key, []).append(ep)
        # Return a list of dicts representing abstracts
        abstracts = [{"topic": k, "count": len(v)} for k, v in groups.items()]
        return abstracts
