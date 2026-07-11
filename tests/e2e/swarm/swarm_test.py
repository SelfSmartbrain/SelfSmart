"""E2E Tests for Swarm Orchestration (Phase 8)."""

from __future__ import annotations

import pytest
import asyncio
from uuid import uuid4

from src.swarm.director import DirectorAgent, SwarmGoal
from src.swarm.sub_orchestrator import SubOrchestrator
from src.swarm.swarm_coordinator import SwarmCoordinator
from src.swarm.task_distributor import TaskDistributor, Task
from src.swarm.load_balancer import LoadBalancer, LoadMetrics


@pytest.mark.asyncio
async def test_director_agent_initialization():
    """Test director agent can be initialized."""
    director = DirectorAgent(max_sub_orchestrators=5)
    await director.initialize()
    
    assert director._running is True
    assert len(director.sub_orchestrators) == 5
    
    await director.shutdown()


@pytest.mark.asyncio
async def test_director_submit_goal():
    """Test director can submit and decompose goals."""
    director = DirectorAgent(max_sub_orchestrators=5)
    await director.initialize()
    
    goal = SwarmGoal(
        description="Build a simple web application",
        priority=7,
        estimated_complexity=5
    )
    
    goal_id = await director.submit_goal(goal)
    
    assert goal_id in director.active_goals
    assert director.active_goals[goal_id].status == "executing"
    
    await director.shutdown()


@pytest.mark.asyncio
async def test_director_monitor_swarm():
    """Test director can monitor swarm status."""
    director = DirectorAgent(max_sub_orchestrators=5)
    await director.initialize()
    
    status = await director.monitor_swarm()
    
    assert status["total_sub_orchestrators"] == 5
    assert status["running"] is True
    assert "idle_sub_orchestrators" in status
    assert "busy_sub_orchestrators" in status
    
    await director.shutdown()


@pytest.mark.asyncio
async def test_director_scale_swarm():
    """Test director can scale swarm up and down."""
    director = DirectorAgent(max_sub_orchestrators=10)
    await director.initialize()
    
    initial_count = len(director.sub_orchestrators)
    assert initial_count == 10
    
    # Scale up
    success = await director.scale_swarm(15)
    assert success is True
    assert len(director.sub_orchestrators) == 15
    
    # Scale down
    success = await director.scale_swarm(5)
    assert success is True
    assert len(director.sub_orchestrators) == 5
    
    await director.shutdown()


@pytest.mark.asyncio
async def test_sub_orchestrator_initialization():
    """Test sub-orchestrator can be initialized."""
    sub_orch = SubOrchestrator(id=uuid4(), director_id=uuid4())
    await sub_orch.initialize()
    
    assert sub_orch._running is True
    assert sub_orch.state.status == "idle"
    
    await sub_orch.shutdown()


@pytest.mark.asyncio
async def test_sub_orchestrator_task_assignment():
    """Test sub-orchestrator can receive and execute tasks."""
    from src.swarm.director import SubOrchestratorAssignment
    
    sub_orch = SubOrchestrator(id=uuid4(), director_id=uuid4())
    await sub_orch.initialize()
    
    assignment = SubOrchestratorAssignment(
        sub_orchestrator_id=sub_orch.id,
        task_description="Test task",
        priority=5
    )
    
    await sub_orch.assign_task(assignment)
    
    # Wait a bit for task to start
    await asyncio.sleep(0.1)
    
    assert sub_orch.state.status == "executing"
    assert sub_orch.state.current_task == "Test task"
    
    await sub_orch.shutdown()


@pytest.mark.asyncio
async def test_sub_orchestrator_progress():
    """Test sub-orchestrator progress tracking."""
    from src.swarm.director import SubOrchestratorAssignment
    
    sub_orch = SubOrchestrator(id=uuid4(), director_id=uuid4())
    await sub_orch.initialize()
    
    assignment = SubOrchestratorAssignment(
        sub_orchestrator_id=sub_orch.id,
        task_description="Test task",
        priority=5
    )
    
    await sub_orch.assign_task(assignment)
    
    # Wait for task to complete
    await asyncio.sleep(6)
    
    assert sub_orch.state.progress == 100.0
    assert sub_orch.state.status == "completed"
    
    await sub_orch.shutdown()


@pytest.mark.asyncio
async def test_swarm_coordinator_initialization():
    """Test swarm coordinator can be initialized."""
    coordinator = SwarmCoordinator(num_directors=3, sub_orchestrators_per_director=5)
    await coordinator.initialize()
    
    assert coordinator._running is True
    assert len(coordinator.directors) == 3
    
    await coordinator.shutdown()


@pytest.mark.asyncio
async def test_swarm_coordinator_submit_goal():
    """Test swarm coordinator can submit goals."""
    coordinator = SwarmCoordinator(num_directors=3, sub_orchestrators_per_director=5)
    await coordinator.initialize()
    
    goal = SwarmGoal(
        description="Build a complex system",
        priority=8,
        estimated_complexity=7
    )
    
    goal_id = await coordinator.submit_goal(goal)
    
    # Verify goal was assigned to a director
    found = False
    for director in coordinator.directors.values():
        if goal_id in director.active_goals:
            found = True
            break
    
    assert found is True
    
    await coordinator.shutdown()


@pytest.mark.asyncio
async def test_swarm_coordinator_metrics():
    """Test swarm coordinator can collect metrics."""
    coordinator = SwarmCoordinator(num_directors=3, sub_orchestrators_per_director=5)
    await coordinator.initialize()
    
    metrics = await coordinator.get_swarm_metrics()
    
    assert metrics.total_directors == 3
    assert metrics.total_sub_orchestrators == 15
    assert metrics.swarm_utilization >= 0.0
    assert metrics.swarm_utilization <= 1.0
    
    await coordinator.shutdown()


@pytest.mark.asyncio
async def test_task_distributor_registration():
    """Test task distributor can register sub-orchestrators."""
    distributor = TaskDistributor()
    
    sub_orch_id = uuid4()
    distributor.register_sub_orchestrator(
        sub_orch_id,
        capabilities=["research", "coding"],
        max_capacity=10
    )
    
    status = distributor.get_sub_orchestrator_status(sub_orch_id)
    assert status is not None
    assert status.capabilities == ["research", "coding"]
    assert status.max_capacity == 10


@pytest.mark.asyncio
async def test_task_distributor_distribution():
    """Test task distributor can distribute tasks."""
    distributor = TaskDistributor()
    
    # Register sub-orchestrators
    sub_orch1 = uuid4()
    sub_orch2 = uuid4()
    distributor.register_sub_orchestrator(sub_orch1, capabilities=["research"])
    distributor.register_sub_orchestrator(sub_orch2, capabilities=["coding"])
    
    # Submit task
    task = Task(
        id=uuid4(),
        description="Research task",
        required_capabilities=["research"],
        priority=5
    )
    
    distributor.submit_task(task)
    
    # Distribute task
    assigned_to = distributor.distribute_task(task)
    
    assert assigned_to == sub_orch1


@pytest.mark.asyncio
async def test_task_distributor_stats():
    """Test task distributor statistics."""
    distributor = TaskDistributor()
    
    sub_orch_id = uuid4()
    distributor.register_sub_orchestrator(
        sub_orch_id,
        capabilities=["research"],
        max_capacity=10
    )
    
    stats = distributor.get_distribution_stats()
    
    assert stats["total_sub_orchestrators"] == 1
    assert stats["total_capacity"] == 10
    assert stats["total_load"] == 0


@pytest.mark.asyncio
async def test_load_balancer_registration():
    """Test load balancer can register sub-orchestrators."""
    balancer = LoadBalancer(strategy="least_loaded")
    
    sub_orch_id = uuid4()
    balancer.register_sub_orchestrator(sub_orch_id)
    
    assert sub_orch_id in balancer.load_metrics


@pytest.mark.asyncio
async def test_load_balancer_selection():
    """Test load balancer can select sub-orchestrator."""
    balancer = LoadBalancer(strategy="least_loaded")
    
    sub_orch1 = uuid4()
    sub_orch2 = uuid4()
    balancer.register_sub_orchestrator(sub_orch1)
    balancer.register_sub_orchestrator(sub_orch2)
    
    # Update metrics with different loads
    metrics1 = LoadMetrics(sub_orchestrator_id=sub_orch1, current_tasks=5)
    metrics2 = LoadMetrics(sub_orchestrator_id=sub_orch2, current_tasks=2)
    balancer.update_metrics(metrics1)
    balancer.update_metrics(metrics2)
    
    # Should select the one with least load
    selected = balancer.select_sub_orchestrator()
    assert selected == sub_orch2


@pytest.mark.asyncio
async def test_load_balancer_round_robin():
    """Test load balancer round-robin strategy."""
    balancer = LoadBalancer(strategy="round_robin")
    
    sub_orch1 = uuid4()
    sub_orch2 = uuid4()
    balancer.register_sub_orchestrator(sub_orch1)
    balancer.register_sub_orchestrator(sub_orch2)
    
    # Should alternate between sub-orchestrators
    selected1 = balancer.select_sub_orchestrator()
    selected2 = balancer.select_sub_orchestrator()
    selected3 = balancer.select_sub_orchestrator()
    
    assert selected1 != selected2
    assert selected3 == selected1


@pytest.mark.asyncio
async def test_load_balancer_task_completion():
    """Test load balancer records task completion."""
    balancer = LoadBalancer(strategy="least_loaded")
    
    sub_orch_id = uuid4()
    balancer.register_sub_orchestrator(sub_orch_id)
    
    # Update metrics with a task
    metrics = LoadMetrics(sub_orchestrator_id=sub_orch_id, current_tasks=1)
    balancer.update_metrics(metrics)
    
    # Record task completion
    balancer.record_task_completion(sub_orch_id, duration=5.0, success=True)
    
    # Check updated metrics
    updated_metrics = balancer.load_metrics[sub_orch_id]
    assert updated_metrics.current_tasks == 0
    assert updated_metrics.avg_task_duration > 0


@pytest.mark.asyncio
async def test_load_balancer_overall_load():
    """Test load balancer overall load calculation."""
    balancer = LoadBalancer(strategy="least_loaded")
    
    sub_orch1 = uuid4()
    sub_orch2 = uuid4()
    balancer.register_sub_orchestrator(sub_orch1)
    balancer.register_sub_orchestrator(sub_orch2)
    
    # Update metrics
    metrics1 = LoadMetrics(sub_orchestrator_id=sub_orch1, current_tasks=3, cpu_usage=50.0, memory_usage=60.0)
    metrics2 = LoadMetrics(sub_orchestrator_id=sub_orch2, current_tasks=2, cpu_usage=40.0, memory_usage=50.0)
    balancer.update_metrics(metrics1)
    balancer.update_metrics(metrics2)
    
    overall = balancer.get_overall_load()
    
    assert overall["total_sub_orchestrators"] == 2
    assert overall["total_tasks"] == 5
    assert overall["avg_cpu_usage"] == 45.0
    assert overall["avg_memory_usage"] == 55.0
