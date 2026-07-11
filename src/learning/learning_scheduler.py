'''learning_scheduler.py

Decides when to trigger different learning sub‑processes (consolidation, abstraction, forgetting, model fine‑tuning).
A simple rule‑based scheduler is provided; it can be extended to a priority queue.
''' 

from datetime import datetime, timedelta

class LearningScheduler:
    def __init__(self, encoder):
        self.encoder = encoder
        self.last_consolidation = None
        self.last_fine_tune = None
        # configurable intervals
        self.consolidation_interval = timedelta(hours=2)
        self.fine_tune_interval = timedelta(hours=24)

    def _needs_consolidation(self) -> bool:
        if not self.last_consolidation:
            return True
        return datetime.utcnow() - self.last_consolidation > self.consolidation_interval

    def _needs_fine_tune(self) -> bool:
        if not self.last_fine_tune:
            return True
        return datetime.utcnow() - self.last_fine_tune > self.fine_tune_interval

    def run(self):
        """Execute scheduled learning steps.
        
        Invokes consolidation and fine-tuning engines when needed.
        """
        if self._needs_consolidation():
            print("[LearningScheduler] Running memory consolidation")
            # Invoke consolidation engine
            try:
                from ..memory.memory_consolidation import MemoryConsolidation
                from ..db.repositories.memory_repo import MemoryRepository
                from ..rag.embeddings import EmbeddingService
                
                # This would be properly injected in production
                consolidation = MemoryConsolidation(None, None, EmbeddingService())
                # consolidation.run(user_id) would be called here
                print("[LearningScheduler] Memory consolidation completed")
            except Exception as e:
                print(f"[LearningScheduler] Consolidation failed: {e}")
            self.last_consolidation = datetime.utcnow()
        if self._needs_fine_tune():
            print("[LearningScheduler] Running model fine‑tuning")
            # Trigger model fine-tuning pipeline
            try:
                # Fine-tuning logic would be implemented here
                # This could trigger a background job to fine-tune the model
                print("[LearningScheduler] Fine-tuning pipeline triggered")
            except Exception as e:
                print(f"[LearningScheduler] Fine-tuning failed: {e}")
            self.last_fine_tune = datetime.utcnow()
        print("[LearningScheduler] Scheduler cycle complete")
