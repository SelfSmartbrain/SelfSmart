from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class BenchmarkMetrics(BaseModel):
    model_config = {"from_attributes": True}
    
    latency_ms: float
    throughput_rps: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float

class ArchitectureBenchmark(BaseModel):
    model_config = {"from_attributes": True}
    
    benchmark_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    candidate_id: uuid.UUID
    run_id: uuid.UUID
    baseline_metrics: BenchmarkMetrics
    candidate_metrics: BenchmarkMetrics
    composite_fitness_score: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BenchmarkRequest(BaseModel):
    model_config = {"from_attributes": True}
    
    candidate_id: uuid.UUID
    run_id: uuid.UUID
    baseline_id: Optional[uuid.UUID] = None
