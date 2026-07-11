'''experiment_runner.py

Orchestrates long‑horizon validation experiments (30 d, 90 d, 180 d).
Uses APScheduler to schedule periodic snapshots of system state and stores them
in the `validation.experiment_runs` table.
''' 

import datetime
from typing import Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, MetaData, Table
from sqlalchemy.orm import sessionmaker
from src.config.settings import get_settings

settings = get_settings()
DATABASE_URL = settings.database_url_sync
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
metadata = MetaData()

experiment_runs = Table(
    "experiment_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("experiment_name", String, nullable=False),
    Column("timestamp", DateTime, default=datetime.datetime.utcnow),
    Column("snapshot", JSON, nullable=False),
)

# Ensure table exists (in real code use Alembic migrations)
metadata.create_all(engine, tables=[experiment_runs])

class ExperimentRunner:
    def __init__(self, experiment_name: str, interval_seconds: int = 3600):
        self.name = experiment_name
        self.interval = interval_seconds
        self.scheduler = BackgroundScheduler()
        self.session = Session()

    def _capture_snapshot(self) -> Dict[str, Any]:
        """Collect metrics from the validation.metrics module.
        This is a placeholder – replace with actual metric calls.
        """
        try:
            from ..validation.metrics import get_all_scores
            scores = get_all_scores()
        except Exception:
            scores = {"placeholder": True}
        return scores

    def _store_snapshot(self, snapshot: Dict[str, Any]):
        ins = experiment_runs.insert().values(
            experiment_name=self.name,
            timestamp=datetime.datetime.utcnow(),
            snapshot=snapshot,
        )
        self.session.execute(ins)
        self.session.commit()
        print(f"[ExperimentRunner] Stored snapshot for {self.name}")

    def _job(self):
        snapshot = self._capture_snapshot()
        self._store_snapshot(snapshot)

    def start(self):
        print(f"[ExperimentRunner] Starting {self.name} (interval {self.interval}s)")
        self.scheduler.add_job(self._job, "interval", seconds=self.interval, id=self.name)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
        self.session.close()
        print(f"[ExperimentRunner] Stopped {self.name}")

# Example usage (commented out for production)
# if __name__ == "__main__":
#     runner30 = ExperimentRunner("30_day_experiment", interval_seconds=86400)
#     runner30.start()
