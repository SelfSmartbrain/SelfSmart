"""Swarm Orchestration API Routes (Phase 8)."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import get_db_session
from src.config.logging import get_logger
from src.swarm.director import DirectorAgent, SwarmGoal, SubOrchestratorAssignment
from src.swarm.swarm_coordinator import SwarmCoordinator, SwarmMetrics

logger = get_logger(__name__)

router = APIRouter(prefix="/swarm", tags=["swarm"])


# ---------------------------------------------------------------------------
# Request/Response Schemas
# ---------------------------------------------------------------------------


class SwarmGoalRequest(BaseModel):
    """Request to submit a swarm goal."""
    
    description: str = Field(..., description="High-level goal description")
    priority: int = Field(5, ge=1, le=10, description="Goal priority")
    estimated_complexity: int = Field(5, ge=1, le=10, description="Estimated complexity")
    required_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    resource_requirements: dict[str, Any] = Field(default_factory=dict)


class SwarmGoalResponse(BaseModel):
    """Response from swarm goal submission."""
    
    goal_id: str
    description: str
    status: str
    sub_task_count: int


class SwarmStatusResponse(BaseModel):
    """Response with swarm status."""
    
    total_directors: int
    total_sub_orchestrators: int
    active_goals: int
    completed_goals: int
    failed_goals: int
    swarm_utilization: float
    running: bool


class DirectorStatusResponse(BaseModel):
    """Response with director status."""
    
    director_id: str
    total_sub_orchestrators: int
    idle_sub_orchestrators: int
    busy_sub_orchestrators: int
    active_goals: int
    total_goals: int
    running: bool


class ScaleRequest(BaseModel):
    """Request to scale the swarm."""
    
    target_directors: int = Field(..., ge=1, le=20, description="Target number of directors")
    target_sub_orchestrators_per_director: int = Field(..., ge=1, le=50, description="Target sub-orchestrators per director")


# ---------------------------------------------------------------------------
# Global Instances
# ---------------------------------------------------------------------------


_swarm_coordinator: SwarmCoordinator | None = None


def get_swarm_coordinator() -> SwarmCoordinator:
    """Get or create swarm coordinator instance."""
    global _swarm_coordinator
    if _swarm_coordinator is None:
        _swarm_coordinator = SwarmCoordinator(
            num_directors=5,
            sub_orchestrators_per_director=10
        )
    return _swarm_coordinator


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/goals", response_model=SwarmGoalResponse)
async def submit_swarm_goal(request: SwarmGoalRequest) -> SwarmGoalResponse:
    """Submit a high-level goal to the swarm."""
    try:
        coordinator = get_swarm_coordinator()
        
        # Initialize coordinator if needed
        if not coordinator._running:
            await coordinator.initialize()
        
        # Create swarm goal
        goal = SwarmGoal(
            description=request.description,
            priority=request.priority,
            estimated_complexity=request.estimated_complexity,
            required_capabilities=request.required_capabilities,
            resource_requirements=request.resource_requirements
        )
        
        # Submit to coordinator
        goal_id = await coordinator.submit_goal(goal)
        
        # Get goal status
        status = await coordinator.get_goal_status(goal_id)
        
        return SwarmGoalResponse(
            goal_id=str(goal_id),
            description=request.description,
            status=status["status"] if status else "pending",
            sub_task_count=status.get("sub_task_count", 0) if status else 0
        )
    except Exception as e:
        logger.error(f"Error submitting swarm goal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goals/{goal_id}")
async def get_swarm_goal_status(goal_id: UUID) -> dict[str, Any]:
    """Get status of a specific swarm goal."""
    try:
        coordinator = get_swarm_coordinator()
        status = await coordinator.get_goal_status(goal_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SwarmStatusResponse)
async def get_swarm_status() -> SwarmStatusResponse:
    """Get overall swarm status and metrics."""
    try:
        coordinator = get_swarm_coordinator()
        metrics = await coordinator.get_swarm_metrics()
        
        return SwarmStatusResponse(
            total_directors=metrics.total_directors,
            total_sub_orchestrators=metrics.total_sub_orchestrators,
            active_goals=metrics.active_goals,
            completed_goals=metrics.completed_goals,
            failed_goals=metrics.failed_goals,
            swarm_utilization=metrics.swarm_utilization,
            running=coordinator._running
        )
    except Exception as e:
        logger.error(f"Error getting swarm status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/directors", response_model=List[DirectorStatusResponse])
async def get_director_status() -> List[DirectorStatusResponse]:
    """Get status of all directors."""
    try:
        coordinator = get_swarm_coordinator()
        statuses = await coordinator.get_director_status()
        
        return [
            DirectorStatusResponse(
                director_id=status["director_id"],
                total_sub_orchestrators=status["total_sub_orchestrators"],
                idle_sub_orchestrators=status["idle_sub_orchestrators"],
                busy_sub_orchestrators=status["busy_sub_orchestrators"],
                active_goals=status["active_goals"],
                total_goals=status["total_goals"],
                running=status["running"]
            )
            for status in statuses
        ]
    except Exception as e:
        logger.error(f"Error getting director status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scale")
async def scale_swarm(request: ScaleRequest) -> dict[str, Any]:
    """Scale the swarm to target size."""
    try:
        coordinator = get_swarm_coordinator()
        
        # Scale directors
        success = await coordinator.scale_directors(request.target_directors)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to scale swarm")
        
        return {
            "status": "scaled",
            "target_directors": request.target_directors,
            "target_sub_orchestrators_per_director": request.target_sub_orchestrators_per_director
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scaling swarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_swarm() -> dict[str, Any]:
    """Initialize the swarm coordinator."""
    try:
        coordinator = get_swarm_coordinator()
        
        if coordinator._running:
            return {"status": "already_initialized"}
        
        await coordinator.initialize()
        
        return {
            "status": "initialized",
            "num_directors": len(coordinator.directors),
            "sub_orchestrators_per_director": coordinator.sub_orchestrators_per_director
        }
    except Exception as e:
        logger.error(f"Error initializing swarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shutdown")
async def shutdown_swarm() -> dict[str, Any]:
    """Shutdown the swarm coordinator."""
    try:
        coordinator = get_swarm_coordinator()
        
        if not coordinator._running:
            return {"status": "already_shutdown"}
        
        await coordinator.shutdown()
        
        return {"status": "shutdown"}
    except Exception as e:
        logger.error(f"Error shutting down swarm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_detailed_metrics() -> dict[str, Any]:
    """Get detailed swarm metrics."""
    try:
        coordinator = get_swarm_coordinator()
        metrics = await coordinator.get_swarm_metrics()
        
        return {
            "metrics": metrics.model_dump(),
            "director_statuses": await coordinator.get_director_status()
        }
    except Exception as e:
        logger.error(f"Error getting detailed metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
