from __future__ import annotations
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from src.config.logging import get_logger
from src.architecture.architecture_benchmark import ArchitectureBenchmark, BenchmarkMetrics, BenchmarkRequest

logger = get_logger(__name__)

async def fetch_baseline_metrics() -> BenchmarkMetrics:
    """
    Mock function to fetch baseline metrics for comparison.
    """
    return BenchmarkMetrics(
        latency_ms=150.0,
        throughput_rps=500.0,
        error_rate=0.01,
        memory_usage_mb=256.0,
        cpu_usage_percent=45.0
    )

async def measure_candidate_metrics(run_id: uuid.UUID) -> BenchmarkMetrics:
    """
    Mock function to measure candidate metrics.
    """
    return BenchmarkMetrics(
        latency_ms=130.0,
        throughput_rps=550.0,
        error_rate=0.005,
        memory_usage_mb=240.0,
        cpu_usage_percent=40.0
    )

async def calculate_composite_fitness(baseline: BenchmarkMetrics, candidate: BenchmarkMetrics) -> float:
    """
    Computes a Composite Fitness Score comparing candidate metrics to baseline.
    Higher is better.
    """
    score = 100.0
    
    if baseline.latency_ms > 0:
        latency_improvement = (baseline.latency_ms - candidate.latency_ms) / baseline.latency_ms
        score += latency_improvement * 20
        
    if baseline.throughput_rps > 0:
        throughput_improvement = (candidate.throughput_rps - baseline.throughput_rps) / baseline.throughput_rps
        score += throughput_improvement * 20
        
    if baseline.error_rate > 0:
        error_improvement = (baseline.error_rate - candidate.error_rate) / baseline.error_rate
        score += error_improvement * 30
        
    if baseline.memory_usage_mb > 0:
        memory_improvement = (baseline.memory_usage_mb - candidate.memory_usage_mb) / baseline.memory_usage_mb
        score += memory_improvement * 15
        
    if baseline.cpu_usage_percent > 0:
        cpu_improvement = (baseline.cpu_usage_percent - candidate.cpu_usage_percent) / baseline.cpu_usage_percent
        score += cpu_improvement * 15
        
    return max(0.0, min(200.0, score))

async def save_architecture_benchmark(benchmark: ArchitectureBenchmark) -> None:
    """
    Mocks saving the benchmark result to a database.
    """
    logger.info(f"Saving ArchitectureBenchmark {benchmark.benchmark_id} to database.")
    await asyncio.sleep(0.1)

async def run_benchmark_for_candidate(request: BenchmarkRequest) -> ArchitectureBenchmark:
    """
    Runs a benchmark comparing the candidate run against the baseline and computes
    a Composite Fitness Score, saving it to ArchitectureBenchmark.
    """
    logger.info(f"Running benchmark for candidate {request.candidate_id}, run_id {request.run_id}")
    
    baseline_metrics = await fetch_baseline_metrics()
    candidate_metrics = await measure_candidate_metrics(request.run_id)
    
    fitness_score = await calculate_composite_fitness(baseline_metrics, candidate_metrics)
    
    benchmark = ArchitectureBenchmark(
        benchmark_id=uuid.uuid4(),
        candidate_id=request.candidate_id,
        run_id=request.run_id,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        composite_fitness_score=fitness_score,
        created_at=datetime.now(timezone.utc)
    )
    
    logger.info(f"Benchmark completed. Composite Fitness Score: {fitness_score}")
    
    await save_architecture_benchmark(benchmark)
    
    return benchmark
