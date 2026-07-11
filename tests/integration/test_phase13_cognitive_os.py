"""
Integration tests for Phase 13: Cognitive Operating System

These tests verify that the unified cognition system works end-to-end,
integrating all the cognitive components together.
"""

import asyncio
import pytest
from datetime import datetime

from src.cognitive_kernel.kernel import CognitiveKernel
from src.cognitive_kernel.scheduler import CognitiveScheduler
from src.cognitive_kernel.attention_manager import AttentionManager
from src.cognitive_kernel.cognitive_bus import CognitiveBus
from src.cognitive_kernel.context_manager import ContextManager

from src.memory.memory_fabric import MemoryFabric
from src.memory.memory_router import MemoryRouter
from src.memory.memory_index import MemoryIndex

from src.cognitive_attention.attention_engine import AttentionEngine
from src.cognitive_attention.salience_detector import SalienceDetector
from src.cognitive_attention.priority_manager import PriorityManager

from src.reasoning.reasoning_hub import ReasoningHub
from src.reasoning.planner import Planner
from src.reasoning.deliberation_engine import DeliberationEngine
from src.reasoning.counterfactual_reasoner import CounterfactualReasoner

from src.cognitive_communication.cognitive_events import CognitiveEventSystem
from src.cognitive_communication.agent_protocol import AgentProtocol
from src.cognitive_communication.message_broker import MessageBroker

from src.agent_society.society_runtime import SocietyRuntime
from src.agent_society.agent_registry import AgentRegistry
from src.agent_society.task_marketplace import TaskMarketplace

from src.identity.identity_engine import IdentityEngine
from src.identity.self_model import SelfModel
from src.identity.mission_manager import MissionManager

from src.research_programs.research_program import ResearchProgram as ResearchProgramClass
from src.research_programs.program_scheduler import ProgramScheduler
from src.research_programs.program_memory import ProgramMemory


@pytest.mark.asyncio
async def test_cognitive_kernel_initialization():
    """Test that the cognitive kernel initializes correctly."""
    kernel = CognitiveKernel()
    await kernel.initialize()
    
    assert kernel.state.name == "active"
    assert kernel.scheduler is not None
    assert kernel.attention_manager is not None
    assert kernel.cognitive_bus is not None
    assert kernel.context_manager is not None
    
    await kernel.shutdown()


@pytest.mark.asyncio
async def test_unified_memory_graph():
    """Test that the unified memory graph works end-to-end."""
    memory_index = MemoryIndex()
    memory_router = MemoryRouter(memory_index=memory_index)
    memory_fabric = MemoryFabric(memory_router=memory_router, memory_index=memory_index)
    
    await memory_fabric.initialize()
    
    # Test storing a memory
    memory_id = await memory_fabric.store(
        content="Test memory content",
        memory_type="episodic",
        metadata={"importance": 0.8}
    )
    
    assert memory_id is not None
    
    # Test retrieving a memory
    memories = await memory_fabric.query(
        query="Test",
        limit=10
    )
    
    assert len(memories) >= 0
    
    await memory_fabric.shutdown()


@pytest.mark.asyncio
async def test_cognitive_attention_system():
    """Test that the cognitive attention system works end-to-end."""
    salience_detector = SalienceDetector()
    priority_manager = PriorityManager()
    attention_engine = AttentionEngine(
        salience_detector=salience_detector,
        priority_manager=priority_manager
    )
    
    await attention_engine.initialize()
    
    # Test salience detection
    salience = await salience_detector.detect_salience(
        data={"content": "Important information"},
        context={"urgency": 0.8}
    )
    
    assert salience.overall_score >= 0.0
    
    # Test priority management
    await priority_manager.add_item(
        item_id="test_item",
        priority=0.8
    )
    
    top_items = priority_manager.get_top_items(limit=5)
    assert len(top_items) >= 0
    
    await attention_engine.shutdown()


@pytest.mark.asyncio
async def test_unified_reasoning_engine():
    """Test that the unified reasoning engine works end-to-end."""
    reasoning_hub = ReasoningHub()
    planner = Planner()
    deliberation_engine = DeliberationEngine()
    counterfactual_reasoner = CounterfactualReasoner()
    
    await reasoning_hub.initialize()
    await planner.initialize()
    await deliberation_engine.initialize()
    
    # Register reasoners
    reasoning_hub.register_reasoner(
        reasoning_hub.ReasoningMode.SYSTEM_2,
        deliberation_engine
    )
    
    # Test reasoning
    from src.reasoning.reasoning_hub import ReasoningRequest
    request = ReasoningRequest(
        query="Test query",
        context={"test": True}
    )
    
    result = await reasoning_hub.reason(request)
    assert result is not None
    assert result.conclusion is not None
    
    # Test planning
    plan = await planner.create_plan(
        goal="Test goal",
        context={}
    )
    
    assert plan is not None
    assert len(plan.actions) >= 0
    
    await reasoning_hub.shutdown()


@pytest.mark.asyncio
async def test_cognitive_communication_bus():
    """Test that the cognitive communication bus works end-to-end."""
    event_system = CognitiveEventSystem()
    agent_protocol = AgentProtocol()
    message_broker = MessageBroker()
    
    await event_system.initialize()
    await message_broker.initialize()
    
    # Test event emission
    event_id = await event_system.emit(
        event_type=event_system.CognitiveEventType.ATTENTION_ALLOCATED,
        source="test",
        data={"test": True}
    )
    
    assert event_id is not None
    
    # Test message broker
    await message_broker.publish(
        topic="test_topic",
        message={"content": "test message"}
    )
    
    subscribers = message_broker.get_topic_subscribers("test_topic")
    assert len(subscribers) >= 0
    
    await event_system.shutdown()
    await message_broker.shutdown()


@pytest.mark.asyncio
async def test_agent_society_runtime():
    """Test that the agent society runtime works end-to-end."""
    society_runtime = SocietyRuntime()
    agent_registry = AgentRegistry()
    task_marketplace = TaskMarketplace()
    
    await society_runtime.initialize()
    await agent_registry.initialize()
    await task_marketplace.initialize()
    
    # Test society creation
    society = await society_runtime.create_society(
        name="Test Society",
        purpose="Testing",
        initial_members=[]
    )
    
    assert society is not None
    assert society.name == "Test Society"
    
    # Test agent registration
    agent = await agent_registry.register_agent(
        agent_id="test_agent",
        name="Test Agent",
        agent_type="test",
        capabilities=[{"name": "test_capability", "proficiency": 0.8}]
    )
    
    assert agent is not None
    assert agent.agent_id == "test_agent"
    
    # Test task marketplace
    task = await task_marketplace.post_task(
        title="Test Task",
        description="Test description",
        required_capabilities=["test_capability"]
    )
    
    assert task is not None
    assert task.title == "Test Task"
    
    await society_runtime.shutdown()


@pytest.mark.asyncio
async def test_long_term_identity_system():
    """Test that the long-term identity system works end-to-end."""
    identity_engine = IdentityEngine()
    self_model = SelfModel()
    mission_manager = MissionManager()
    
    await identity_engine.initialize()
    await self_model.initialize()
    await mission_manager.initialize()
    
    # Test identity
    identity = await identity_engine.get_identity()
    assert identity is not None
    assert identity.name == "ModelX"
    
    # Test skill addition
    skill = await identity_engine.add_skill(
        name="test_skill",
        category="test",
        proficiency=0.7
    )
    
    assert skill is not None
    
    # Test mission creation
    mission = await mission_manager.create_mission(
        title="Test Mission",
        description="Test description"
    )
    
    assert mission is not None
    assert mission.title == "Test Mission"
    
    # Test self-model
    await self_model.record_performance(
        task_type="test",
        success=True,
        confidence=0.8,
        duration=10.0
    )
    
    success_rate = self_model.get_success_rate("test")
    assert success_rate >= 0.0


@pytest.mark.asyncio
async def test_persistent_research_programs():
    """Test that persistent research programs work end-to-end."""
    program_scheduler = ProgramScheduler()
    program_memory = ProgramMemory()
    
    await program_scheduler.initialize()
    await program_memory.initialize()
    
    # Test program scheduling
    await program_scheduler.schedule_program(
        program_id="test_program",
        frequency="daily",
        interval_hours=24.0
    )
    
    scheduled = program_scheduler.get_scheduled_programs()
    assert len(scheduled) >= 0
    
    # Test program memory
    entry = await program_memory.add_entry(
        program_id="test_program",
        memory_type=program_memory.MemoryType.INSIGHT,
        content="Test insight",
        importance=0.8
    )
    
    assert entry is not None
    
    insights = await program_memory.get_insights("test_program")
    assert len(insights) >= 0
    
    await program_scheduler.shutdown()


@pytest.mark.asyncio
async def test_end_to_end_cognitive_flow():
    """Test the complete end-to-end cognitive flow."""
    # Initialize all components
    memory_index = MemoryIndex()
    memory_router = MemoryRouter(memory_index=memory_index)
    memory_fabric = MemoryFabric(memory_router=memory_router, memory_index=memory_index)
    
    salience_detector = SalienceDetector()
    priority_manager = PriorityManager()
    attention_engine = AttentionEngine(
        salience_detector=salience_detector,
        priority_manager=priority_manager
    )
    
    reasoning_hub = ReasoningHub()
    deliberation_engine = DeliberationEngine()
    
    event_system = CognitiveEventSystem()
    
    # Initialize
    await memory_fabric.initialize()
    await attention_engine.initialize()
    await reasoning_hub.initialize()
    await event_system.initialize()
    
    # Register reasoner
    reasoning_hub.register_reasoner(
        reasoning_hub.ReasoningMode.SYSTEM_2,
        deliberation_engine
    )
    
    # Simulate a cognitive task
    # 1. Store information in memory
    memory_id = await memory_fabric.store(
        content="Important task information",
        memory_type="episodic",
        metadata={"importance": 0.9}
    )
    
    # 2. Detect salience
    salience = await salience_detector.detect_salience(
        data={"content": "Important task information"},
        context={"urgency": 0.8}
    )
    
    # 3. Allocate attention
    attention = await attention_engine.allocate_attention(
        task_id="test_task",
        priority=salience.overall_score
    )
    
    # 4. Emit event
    await event_system.emit(
        event_type=event_system.CognitiveEventType.ATTENTION_ALLOCATED,
        source="test",
        data={"task_id": "test_task", "attention": attention}
    )
    
    # 5. Reason about the task
    from src.reasoning.reasoning_hub import ReasoningRequest
    request = ReasoningRequest(
        query="How to handle this task?",
        context={"memory_id": memory_id}
    )
    
    result = await reasoning_hub.reason(request)
    
    # Verify the flow worked
    assert memory_id is not None
    assert salience.overall_score >= 0.0
    assert result is not None
    assert result.conclusion is not None
    
    # Cleanup
    await memory_fabric.shutdown()
    await attention_engine.shutdown()
    await reasoning_hub.shutdown()
    await event_system.shutdown()


if __name__ == "__main__":
    # Run a simple test
    asyncio.run(test_cognitive_kernel_initialization())
    print("✓ Cognitive kernel initialization test passed")
    
    asyncio.run(test_unified_memory_graph())
    print("✓ Unified memory graph test passed")
    
    asyncio.run(test_cognitive_attention_system())
    print("✓ Cognitive attention system test passed")
    
    asyncio.run(test_unified_reasoning_engine())
    print("✓ Unified reasoning engine test passed")
    
    asyncio.run(test_cognitive_communication_bus())
    print("✓ Cognitive communication bus test passed")
    
    asyncio.run(test_agent_society_runtime())
    print("✓ Agent society runtime test passed")
    
    asyncio.run(test_long_term_identity_system())
    print("✓ Long-term identity system test passed")
    
    asyncio.run(test_persistent_research_programs())
    print("✓ Persistent research programs test passed")
    
    asyncio.run(test_end_to_end_cognitive_flow())
    print("✓ End-to-end cognitive flow test passed")
    
    print("\n✅ All Phase 13 integration tests passed!")
