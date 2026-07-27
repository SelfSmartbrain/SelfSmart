from celery import Celery
from src.config.settings import get_settings

settings = get_settings()

app = Celery(
    "smartself",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks.learning_tasks", "src.tasks.training_tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 6,  # 6 hours limit for training
)

if __name__ == "__main__":
    app.start()
