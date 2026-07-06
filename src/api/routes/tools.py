from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.tools import (
    CapabilityGapCreate,
    CapabilityGapResponse,
    ToolBenchmarkCreate,
    ToolBenchmarkResponse,
    ToolCreate,
    ToolResponse,
    ToolVersionCreate,
    ToolVersionResponse,
)
from src.config.logging import get_logger
from src.db.models import CapabilityGap, Tool, ToolBenchmark, ToolVersion
from src.db.session import get_session

logger = get_logger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/gaps", response_model=CapabilityGapResponse, status_code=201)
async def create_gap(
    gap: CapabilityGapCreate,
    db: AsyncSession = Depends(get_session),
):
    logger.info("Creating capability gap", description=gap.description)
    new_gap = CapabilityGap(**gap.model_dump())
    db.add(new_gap)
    await db.commit()
    await db.refresh(new_gap)
    return new_gap


@router.get("/gaps", response_model=list[CapabilityGapResponse])
async def list_gaps(db: AsyncSession = Depends(get_session)):
    logger.info("Listing capability gaps")
    result = await db.execute(select(CapabilityGap))
    return result.scalars().all()


@router.post("/", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool: ToolCreate,
    db: AsyncSession = Depends(get_session),
):
    logger.info(f"Creating tool: {tool.name}")
    new_tool = Tool(**tool.model_dump())
    db.add(new_tool)
    await db.commit()
    await db.refresh(new_tool)
    return new_tool


@router.get("/", response_model=list[ToolResponse])
async def list_tools(db: AsyncSession = Depends(get_session)):
    logger.info("Listing tools")
    result = await db.execute(select(Tool))
    return result.scalars().all()


@router.post("/versions", response_model=ToolVersionResponse, status_code=201)
async def create_tool_version(
    version: ToolVersionCreate,
    db: AsyncSession = Depends(get_session),
):
    logger.info(f"Creating tool version for tool ID: {version.tool_id}")
    new_version = ToolVersion(**version.model_dump())
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)
    return new_version


@router.get("/versions", response_model=list[ToolVersionResponse])
async def list_tool_versions(
    tool_id: UUID | None = None,
    db: AsyncSession = Depends(get_session),
):
    logger.info("Listing tool versions")
    stmt = select(ToolVersion)
    if tool_id:
        stmt = stmt.where(ToolVersion.tool_id == tool_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/benchmarks", response_model=ToolBenchmarkResponse, status_code=201)
async def create_tool_benchmark(
    benchmark: ToolBenchmarkCreate,
    db: AsyncSession = Depends(get_session),
):
    logger.info(f"Creating tool benchmark for version ID: {benchmark.tool_version_id}")
    new_benchmark = ToolBenchmark(**benchmark.model_dump())
    db.add(new_benchmark)
    await db.commit()
    await db.refresh(new_benchmark)
    return new_benchmark


@router.get("/benchmarks", response_model=list[ToolBenchmarkResponse])
async def list_tool_benchmarks(
    tool_version_id: UUID | None = None,
    db: AsyncSession = Depends(get_session),
):
    logger.info("Listing tool benchmarks")
    stmt = select(ToolBenchmark)
    if tool_version_id:
        stmt = stmt.where(ToolBenchmark.tool_version_id == tool_version_id)
    result = await db.execute(stmt)
    return result.scalars().all()
