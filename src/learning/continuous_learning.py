'''continuous_learning.py

Orchestrates periodic learning cycles that update the cognitive core based on new experiences.
The scheduler triggers encoding, consolidation, and optional model fine‑tuning.
''' 

from datetime import datetime, timedelta
from threading import Timer
from .experience_encoder import ExperienceEncoder
from .learning_scheduler import LearningScheduler

class ContinuousLearning:
    def __init__(self, db_session, semantic_mem, schedule_interval_seconds: int = 3600):
        self.db = db_session
        self.semantic_mem = semantic_mem
        self.encoder = ExperienceEncoder(db_session, semantic_mem)
        self.scheduler = LearningScheduler(self.encoder)
        self.interval = schedule_interval_seconds
        self._timer = None

    def _run_cycle(self):
        print(f"[ContinuousLearning] Running learning cycle at {datetime.utcnow()}")
        self.scheduler.run()
        # Re‑schedule the next run
        self._timer = Timer(self.interval, self._run_cycle)
        self._timer.start()

    def start(self):
        print("[ContinuousLearning] Starting periodic learning cycles")
        self._run_cycle()

    def stop(self):
        if self._timer:
            self._timer.cancel()
            print("[ContinuousLearning] Stopped")

    def __repr__(self):
        return f"ContinuousLearning(interval={self.interval}s)"
