"""Celery tasks for continuous learning pipeline."""

import asyncio
import logging
from src.tasks.celery_app import app
from src.learning.continuous_learner import ContinuousLearner, LearningConfig

logger = logging.getLogger(__name__)


async def _run_learning_loop() -> dict:
    """Async function to run the continuous learning loop."""
    logger.info("Starting continuous learning task...")
    config = LearningConfig()
    learner = ContinuousLearner(config)
    try:
        await learner.start_learning()
        stats = learner.stats.__dict__ if hasattr(learner, "stats") else {}
        return {"status": "completed", "stats": stats}
    except Exception as e:
        logger.error(f"Learning task failed: {e}")
        raise


@app.task(bind=True, name="src.tasks.learning_tasks.run_learning_loop")
def run_learning_loop(self):
    """Celery task to run the continuous learning loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_learning_loop())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Learning task failed: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)
