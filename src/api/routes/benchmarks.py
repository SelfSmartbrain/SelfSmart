from __future__ import annotations

from typing import AsyncGenerator, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger
from src.api.schemas.benchmarks import (
    BenchmarkRun,
    BenchmarkRunCreate,
    BenchmarkRunUpdate,
    BenchmarkMetric,
    BenchmarkMetricCreate,
    StrategyComparison,
    StrategyComparisonCreate,
    SkillValidation,
    SkillValidationCreate
)

logger = get_logger(__name__)
router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# Placeholder dependency for DB session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    yield None  # type: ignore

@router.post("/runs", response_model=BenchmarkRun, status_code=status.HTTP_201_CREATED)
async def create_benchmark_run(
    run_in: BenchmarkRunCreate,
    db: AsyncSession = Depends(get_db_session)
) -> BenchmarkRun:
    logger.info(f"Creating benchmark run: {run_in.name}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/runs/{run_id}", response_model=BenchmarkRun)
async def get_benchmark_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> BenchmarkRun:
    logger.info(f"Getting benchmark run: {run_id}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/runs", response_model=List[BenchmarkRun])
async def list_benchmark_runs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> List[BenchmarkRun]:
    logger.info("Listing benchmark runs")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.patch("/runs/{run_id}", response_model=BenchmarkRun)
async def update_benchmark_run(
    run_id: UUID,
    run_in: BenchmarkRunUpdate,
    db: AsyncSession = Depends(get_db_session)
) -> BenchmarkRun:
    logger.info(f"Updating benchmark run: {run_id}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/metrics", response_model=BenchmarkMetric, status_code=status.HTTP_201_CREATED)
async def create_benchmark_metric(
    metric_in: BenchmarkMetricCreate,
    db: AsyncSession = Depends(get_db_session)
) -> BenchmarkMetric:
    logger.info(f"Creating benchmark metric for run: {metric_in.run_id}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/runs/{run_id}/metrics", response_model=List[BenchmarkMetric])
async def list_benchmark_metrics(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> List[BenchmarkMetric]:
    logger.info(f"Listing benchmark metrics for run: {run_id}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/strategies/compare", response_model=StrategyComparison, status_code=status.HTTP_201_CREATED)
async def create_strategy_comparison(
    comparison_in: StrategyComparisonCreate,
    db: AsyncSession = Depends(get_db_session)
) -> StrategyComparison:
    logger.info("Creating strategy comparison")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/skills/validate", response_model=SkillValidation, status_code=status.HTTP_201_CREATED)
async def create_skill_validation(
    validation_in: SkillValidationCreate,
    db: AsyncSession = Depends(get_db_session)
) -> SkillValidation:
    logger.info("Creating skill validation")
    raise HTTPException(status_code=501, detail="Not implemented")
