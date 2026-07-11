'''forgetting_engine.py

Engine that prunes low‑utility memories based on a simple utility score.

Current implementation uses a placeholder heuristic: keep only the most recent N entries
or those with a non‑null ``outcome`` indicating a meaningful event.
''' 

from typing import List
from sqlalchemy.orm import Session
from ..memory.episodic_memory import EpisodicMemory

class ForgettingEngine:
    def __init__(self, db_session: Session, retain_limit: int = 1000):
        self.db = db_session
        self.retain_limit = retain_limit

    def prune(self) -> None:
        """Delete old or low‑utility episodic memories.
        
        This stub retains the newest ``retain_limit`` rows ordered by timestamp.
        """
        # Fetch IDs to keep
        keep_ids = (
            self.db.query(EpisodicMemory.id)
            .order_by(EpisodicMemory.timestamp.desc())
            .limit(self.retain_limit)
            .all()
        )
        keep_ids = [id_[0] for id_ in keep_ids]
        # Delete others
        self.db.query(EpisodicMemory).filter(~EpisodicMemory.id.in_(keep_ids)).delete(synchronize_session=False)
        self.db.commit()
        print(f"ForgettingEngine: retained {len(keep_ids)} episodes, pruned others")
