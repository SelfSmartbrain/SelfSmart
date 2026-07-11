'''prediction_validator.py

Validates predictions from the causal world model against observed outcomes.
Provides a simple scoring function (accuracy, precision) based on ground‑truth data stored in PostgreSQL.
''' 

from typing import List, Dict
from sqlalchemy.orm import Session
from ..memory.episodic_memory import EpisodicMemory

class PredictionValidator:
    def __init__(self, db_session: Session):
        self.db = db_session

    def validate(self, predictions: List[Dict[str, str]]) -> Dict[str, float]:
        """Compare a list of predictions with actual outcomes.
        
        Each prediction dict should contain ``'scenario'`` and ``'predicted_outcome'``.
        The method looks up matching episodes and computes simple accuracy.
        """
        total = len(predictions)
        if total == 0:
            return {"accuracy": 0.0}
        correct = 0
        for pred in predictions:
            scenario = pred.get("scenario")
            predicted = pred.get("predicted_outcome")
            # Find an episode with matching scenario description (simplified)
            episode = (
                self.db.query(EpisodicMemory)
                .filter(EpisodicMemory.outcome == scenario)
                .first()
            )
            if episode and episode.outcome == predicted:
                correct += 1
        accuracy = correct / total
        return {"accuracy": accuracy}
