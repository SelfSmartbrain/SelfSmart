from __future__ import annotations
import asyncio
import time
import random
from datetime import datetime, timezone
from pydantic import BaseModel
from src.config.logging import get_logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = get_logger(__name__)


class WorkerMetrics(BaseModel):
    jobs_submitted: int
    jobs_completed: int
    jobs_failed: int
    duration_sec: float
    throughput_per_sec: float
    avg_job_duration_ms: float
    model_config = {"from_attributes": True}


class WorkerStressTester:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.completed = 0
        self.failed = 0
        self.job_durations = []

    async def realistic_job(self) -> None:
        """
        Simulate a realistic workload job with variable duration and potential failures.
        This mimics actual production workloads rather than dummy operations.
        """
        try:
            # Simulate variable job duration (5-50ms) to match production characteristics
            duration_ms = random.uniform(5, 50)
            await asyncio.sleep(duration_ms / 1000.0)

            # Simulate occasional failures (2% failure rate)
            if random.random() < 0.02:
                raise RuntimeError("Simulated job failure")

            # Simulate occasional longer-running jobs (5% of jobs take 100-200ms)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(100, 200) / 1000.0)

            self.completed += 1
            self.job_durations.append(duration_ms)

        except Exception as e:
            self.failed += 1
            logger.debug(f"Job failed: {e}")

    async def run_stress_test(self, job_count: int = 1000) -> WorkerMetrics:
        """
        Run a stress test with realistic workload simulation.

        Jobs simulate production characteristics:
        - Variable duration (5-50ms typical, 100-200ms for complex jobs)
        - 2% failure rate
        - 5% of jobs are complex (longer duration)
        """
        logger.info(f"Loading APScheduler with {job_count} realistic jobs...")
        self.scheduler.start()
        start_time = time.perf_counter()

        # Schedule all jobs as quickly as possible
        now = datetime.now(timezone.utc)
        for _ in range(job_count):
            self.scheduler.add_job(self.realistic_job, "date", run_date=now)

        # Wait for completion with timeout
        timeout = 300  # 5 minutes max
        elapsed = 0
        while (self.completed + self.failed) < job_count and elapsed < timeout:
            await asyncio.sleep(0.1)
            elapsed += 0.1

        duration = time.perf_counter() - start_time
        self.scheduler.shutdown()

        # Calculate average job duration for successful jobs
        avg_duration = (
            sum(self.job_durations) / len(self.job_durations) if self.job_durations else 0.0
        )

        logger.info(
            f"Stress test completed: {self.completed} succeeded, {self.failed} failed, "
            f"{duration:.2f}s duration, {job_count/duration:.2f} jobs/sec"
        )

        return WorkerMetrics(
            jobs_submitted=job_count,
            jobs_completed=self.completed,
            jobs_failed=self.failed,
            duration_sec=duration,
            throughput_per_sec=job_count / duration if duration > 0 else 0.0,
            avg_job_duration_ms=avg_duration,
        )
