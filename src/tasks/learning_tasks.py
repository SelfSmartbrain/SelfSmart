import asyncio
import logging
from src.tasks.celery_app import app
from src.learning.continuous_learner import ContinuousLearner, LearningConfig

logger = logging.getLogger(__name__)

@app.task(bind=True, name="src.tasks.learning_tasks.run_learning_loop")
def run_learning_loop(self):
    """Celery task to run the continuous learning loop."""
    logger.info("Starting continuous learning task...")
    
    # Initialize learner
    config = LearningConfig()
    learner = ContinuousLearner(config)
    
    # Use a flag in Redis to allow remote stopping
    # In a real senior implementation, we'd check a Redis key in the loop
    
    try:
        # Run the async learning loop in the Celery worker
        loop = asyncio.get_event_loop()
        loop.run_until_complete(learner.start_learning())
    except Exception as e:
        logger.error(f"Learning task failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
    
    return {"status": "completed", "stats": learner.stats.__dict__ if hasattr(learner, 'stats') else {}}
