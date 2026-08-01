"""
Unit tests for Swarm Coordinator - Phase 5: Swarm Communication & Load Balancer Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone

from src.swarm.swarm_coordinator import (
    SwarmCoordinator,
    SwarmMetrics,
    InProcessMessageRouter,
    ConsensusEvaluator,
    LoadBalancer,
    SwarmMessage,
    MessageType,
    message_router,
    consensus_evaluator,
    load_balancer,
)
from src.swarm.director import DirectorAgent, SwarmGoal


class TestMessageType:
    """Test MessageType enum"""
    
    def test_message_types(self):
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.TASK_RESULT.value == "task_result"
        assert MessageType.CONSENSUS_VOTE.value == "consensus_vote"
        assert MessageType.CONSENSUS_RESULT.value == "consensus_result"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.LOAD_REPORT.value == "load_report"
        assert MessageType.SCALING_SIGNAL.value == "scaling_signal"


class TestSwarmMessage:
    """Test SwarmMessage dataclass"""
    
    def test_message_creation(self):
        sender = uuid4()
        recipient = uuid4()
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender_id=sender,
            recipient_id=recipient,
            payload={"task": "test"},
        )
        
        assert msg.msg_type == MessageType.TASK_ASSIGNMENT
        assert msg.sender_id == sender
        assert msg.recipient_id == recipient
        assert msg.payload == {"task": "test"}
        assert msg.correlation_id is None
        assert msg.reply_to is None
    
    def test_broadcast_message(self):
        sender = uuid4()
        msg = SwarmMessage(
            msg_type=MessageType.HEARTBEAT,
            sender_id=sender,
            recipient_id=None,  # broadcast
            payload={"status": "alive"},
        )
        
        assert msg.recipient_id is None


class TestInProcessMessageRouter:
    """Test InProcessMessageRouter"""
    
    @pytest.fixture
    def router(self):
        return InProcessMessageRouter()
    
    @pytest.fixture
    def agent_id(self):
        return uuid4()
    
    @pytest.mark.asyncio
    async def test_register_agent(self, router, agent_id):
        queue = router.register_agent(agent_id)
        
        assert isinstance(queue, asyncio.Queue)
        assert agent_id in router._queues
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, router, agent_id):
        router.register_agent(agent_id)
        router.unregister_agent(agent_id)
        
        assert agent_id not in router._queues
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, router, agent_id):
        router.register_agent(agent_id)
        router.subscribe(agent_id, MessageType.TASK_ASSIGNMENT)
        
        assert agent_id in router._subscriptions[MessageType.TASK_ASSIGNMENT]
        
        router.unsubscribe(agent_id, MessageType.TASK_ASSIGNMENT)
        
        assert agent_id not in router._subscriptions[MessageType.TASK_ASSIGNMENT]
    
    @pytest.mark.asyncio
    async def test_send_direct_message(self, router, agent_id):
        recipient_id = uuid4()
        router.register_agent(agent_id)
        router.register_agent(recipient_id)
        
        msg = SwarmMessage(
            msg_type=MessageType.TASK_ASSIGNMENT,
            sender_id=agent_id,
            recipient_id=recipient_id,
            payload={"task": "test"},
        )
        
        await router.send(msg)
        
        # Check recipient received it
        received = await router.receive(recipient_id, timeout=0.1)
        assert received is not None
        assert received.payload == {"task": "test"}
    
    @pytest.mark.asyncio
    async def test_send_broadcast_message(self, router):
        sender = uuid4()
        recipient1 = uuid4()
        recipient2 = uuid4()
        
        router.register_agent(sender)
        router.register_agent(recipient1)
        router.register_agent(recipient2)
        
        # Start router to process broadcasts
        await router.start()
        
        msg = SwarmMessage(
            msg_type=MessageType.HEARTBEAT,
            sender_id=sender,
            recipient_id=None,  # broadcast
            payload={"status": "alive"},
        )
        
        await router.send(msg)
        
        # Wait a bit for routing
        await asyncio.sleep(0.1)
        
        # Both recipients should receive
        received1 = await router.receive(recipient1, timeout=0.5)
        received2 = await router.receive(recipient2, timeout=0.5)
        
        await router.stop()
        
        assert received1 is not None
        assert received2 is not None
        assert received1.payload == {"status": "alive"}
    
    @pytest.mark.asyncio
    async def test_start_stop(self, router):
        await router.start()
        assert router._running is True
        assert router._router_task is not None
        
        await router.stop()
        assert router._running is False


class TestConsensusEvaluator:
    """Test ConsensusEvaluator"""
    
    @pytest.fixture
    def evaluator(self):
        return ConsensusEvaluator(min_agreement=0.66)
    
    @pytest.fixture
    def voters(self):
        return [uuid4() for _ in range(5)]
    
    def test_register_voter(self, evaluator, voters):
        voter = voters[0]
        evaluator.register_voter(voter, weight=2.0)
        
        assert evaluator._vote_weights[voter] == 2.0
    
    def test_unregister_voter(self, evaluator, voters):
        voter = voters[0]
        evaluator.register_voter(voter)
        evaluator.unregister_voter(voter)
        
        assert voter not in evaluator._vote_weights
    
    def test_submit_vote(self, evaluator, voters):
        proposal_id = uuid4()
        voter = voters[0]
        
        evaluator.submit_vote(proposal_id, voter, {"agree": True})
        
        assert proposal_id in evaluator._votes
        assert evaluator._votes[proposal_id][voter] == {"agree": True}
    
    def test_evaluate_consensus_reached(self, evaluator, voters):
        proposal_id = uuid4()
        
        # 4 out of 5 agree (80% > 66%)
        for i, voter in enumerate(voters):
            evaluator.register_voter(voter, weight=1.0)
            if i < 4:
                evaluator.submit_vote(proposal_id, voter, {"agree": True})
            else:
                evaluator.submit_vote(proposal_id, voter, {"agree": False})
        
        result = evaluator.evaluate(proposal_id)
        
        assert result["consensus"] is True
        assert result["agreement_ratio"] == 0.8
        assert result["winning_vote"] == "{'agree': True}"
    
    def test_evaluate_consensus_not_reached(self, evaluator, voters):
        proposal_id = uuid4()
        
        # 3 out of 5 agree (60% < 66%)
        for i, voter in enumerate(voters):
            evaluator.register_voter(voter, weight=1.0)
            if i < 3:
                evaluator.submit_vote(proposal_id, voter, {"agree": True})
            else:
                evaluator.submit_vote(proposal_id, voter, {"agree": False})
        
        result = evaluator.evaluate(proposal_id)
        
        assert result["consensus"] is False
        assert result["agreement_ratio"] == 0.6
    
    def test_evaluate_no_votes(self, evaluator):
        proposal_id = uuid4()
        
        result = evaluator.evaluate(proposal_id)
        
        assert result["consensus"] is False
        assert result["reason"] == "No votes submitted"
    
    def test_clear_proposal(self, evaluator, voters):
        proposal_id = uuid4()
        voter = voters[0]
        
        evaluator.submit_vote(proposal_id, voter, {"agree": True})
        evaluator.clear_proposal(proposal_id)
        
        assert proposal_id not in evaluator._votes


class TestLoadBalancer:
    """Test LoadBalancer"""
    
    @pytest.fixture
    def balancer(self):
        return LoadBalancer()
    
    @pytest.fixture
    def agents(self):
        return [uuid4() for _ in range(3)]
    
    def test_register_agent(self, balancer, agents):
        agent = agents[0]
        balancer.register_agent(agent, ["coding", "testing"], max_load=1.0)
        
        assert agent in balancer._agent_loads
        assert agent in balancer._agent_capabilities
        assert agent in balancer._agent_status
        assert balancer._agent_capabilities[agent] == ["coding", "testing"]
        assert balancer._agent_status[agent] == "idle"
    
    def test_unregister_agent(self, balancer, agents):
        agent = agents[0]
        balancer.register_agent(agent)
        balancer.unregister_agent(agent)
        
        assert agent not in balancer._agent_loads
        assert agent not in balancer._agent_capabilities
        assert agent not in balancer._agent_status
        assert agent not in balancer._task_history
    
    def test_update_load(self, balancer, agents):
        agent = agents[0]
        balancer.register_agent(agent)
        
        balancer.update_load(agent, 0.7)
        
        assert balancer._agent_loads[agent] == 0.7
        assert balancer._agent_status[agent] == "busy"
        
        balancer.update_load(agent, 0.0)
        assert balancer._agent_status[agent] == "idle"
    
    def test_update_status(self, balancer, agents):
        agent = agents[0]
        balancer.register_agent(agent)
        
        balancer.update_status(agent, "offline")
        assert balancer._agent_status[agent] == "offline"
    
    def test_record_task_completion(self, balancer, agents):
        agent = agents[0]
        balancer.register_agent(agent)
        
        balancer.record_task_completion(agent, {"task_id": "123", "duration": 100})
        
        assert len(balancer._task_history[agent]) == 1
        assert balancer._task_history[agent][0]["task_id"] == "123"
    
    def test_select_agent_least_loaded(self, balancer, agents):
        for agent in agents:
            balancer.register_agent(agent, ["coding"])
        
        balancer.update_load(agents[0], 0.8)
        balancer.update_load(agents[1], 0.3)
        balancer.update_load(agents[2], 0.5)
        
        selected = balancer.select_agent(required_capabilities=["coding"], strategy="least_loaded")
        
        assert selected == agents[1]  # Least loaded
    
    def test_select_agent_most_capable(self, balancer, agents):
        balancer.register_agent(agents[0], ["coding"])
        balancer.register_agent(agents[1], ["coding", "testing", "docs"])
        balancer.register_agent(agents[2], ["coding", "testing"])
        
        selected = balancer.select_agent(required_capabilities=["coding"], strategy="most_capable")
        
        assert selected == agents[1]  # Most capabilities
    
    def test_select_agent_round_robin(self, balancer, agents):
        for agent in agents:
            balancer.register_agent(agent, ["coding"])
        
        # Add task history
        balancer.record_task_completion(agents[0], {})
        balancer.record_task_completion(agents[0], {})
        balancer.record_task_completion(agents[1], {})
        
        selected = balancer.select_agent(required_capabilities=["coding"], strategy="round_robin")
        
        assert selected == agents[2]  # Least tasks
    
    def test_select_agent_no_candidates(self, balancer, agents):
        balancer.register_agent(agents[0], ["testing"])
        
        selected = balancer.select_agent(required_capabilities=["coding"])
        
        assert selected is None
    
    def test_select_agent_offline_excluded(self, balancer, agents):
        balancer.register_agent(agents[0], ["coding"])
        balancer.register_agent(agents[1], ["coding"])
        balancer.update_status(agents[0], "offline")
        
        selected = balancer.select_agent(required_capabilities=["coding"])
        
        assert selected == agents[1]
    
    def test_get_load_report(self, balancer, agents):
        balancer.register_agent(agents[0], ["coding"])
        balancer.register_agent(agents[1], ["testing"])
        balancer.update_load(agents[0], 0.5)  # This makes it "busy" (load > 0.1)
        balancer.update_status(agents[1], "offline")  # This one is offline
        
        report = balancer.get_load_report()
        
        assert report["total_agents"] == 2
        assert report["busy_agents"] == 1  # agents[0] has load 0.5
        assert report["idle_agents"] == 0  # agents[1] is offline, not idle
        assert str(agents[0]) in report["agent_loads"]


class TestSwarmCoordinator:
    """Test SwarmCoordinator"""
    
    @pytest.fixture
    def coordinator(self):
        return SwarmCoordinator(num_directors=2, sub_orchestrators_per_director=3)
    
    def test_init(self, coordinator):
        assert coordinator.num_directors == 2
        assert coordinator.sub_orchestrators_per_director == 3
        assert coordinator.directors == {}
        assert coordinator._running is False
    
    @pytest.mark.asyncio
    async def test_initialize(self, coordinator):
        with patch('src.swarm.swarm_coordinator.DirectorAgent') as mock_director_class:
            mock_director = AsyncMock()
            mock_director.initialize = AsyncMock()
            mock_director_class.return_value = mock_director
            
            await coordinator.initialize()
            
            assert len(coordinator.directors) == 2
            assert coordinator._running is True
            assert coordinator._monitor_task is not None
            assert mock_director_class.call_count == 2
    
    @pytest.mark.asyncio
    async def test_shutdown(self, coordinator):
        mock_director = AsyncMock()
        mock_director.shutdown = AsyncMock()
        director_id = uuid4()
        coordinator.directors[director_id] = mock_director
        coordinator._running = True
        coordinator._monitor_task = asyncio.create_task(asyncio.sleep(10))
        
        await coordinator.shutdown()
        
        assert coordinator._running is False
        mock_director.shutdown.assert_called_once()
        assert coordinator.directors == {}
    
    @pytest.mark.asyncio
    async def test_submit_goal(self, coordinator):
        mock_director = AsyncMock()
        mock_director.submit_goal = AsyncMock(return_value=uuid4())
        mock_director.monitor_swarm = AsyncMock(return_value={
            "busy_sub_orchestrators": 1,
            "total_sub_orchestrators": 3,
        })
        director_id = uuid4()
        coordinator.directors[director_id] = mock_director
        coordinator._running = True
        
        # Mock load balancer
        coordinator._load_balancer.select_agent = Mock(return_value=director_id)
        
        goal = SwarmGoal(description="Test goal", priority=5)
        goal_id = await coordinator.submit_goal(goal)
        
        assert goal_id is not None
        mock_director.submit_goal.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_consensus(self, coordinator):
        mock_director = AsyncMock()
        director_id = uuid4()
        coordinator.directors[director_id] = mock_director
        coordinator._running = True
        
        proposal = {"action": "scale_up", "reason": "high_load"}
        result = await coordinator.request_consensus(proposal)
        
        assert "consensus" in result
        assert "agreement_ratio" in result
    
    @pytest.mark.asyncio
    async def test_get_swarm_metrics(self, coordinator):
        mock_director = AsyncMock()
        mock_director.monitor_swarm = AsyncMock(return_value={
            "total_sub_orchestrators": 3,
            "busy_sub_orchestrators": 2,
            "active_goals": 1,
        })
        mock_director.active_goals = {
            uuid4(): Mock(status="completed"),
            uuid4(): Mock(status="executing"),
        }
        director_id = uuid4()
        coordinator.directors[director_id] = mock_director
        
        metrics = await coordinator.get_swarm_metrics()
        
        assert isinstance(metrics, SwarmMetrics)
        assert metrics.total_directors == 1
        assert metrics.total_sub_orchestrators == 3
        assert metrics.active_goals == 1
        assert metrics.completed_goals == 1
        assert metrics.swarm_utilization > 0
    
    @pytest.mark.asyncio
    async def test_scale_directors_up(self, coordinator):
        with patch('src.swarm.swarm_coordinator.DirectorAgent') as mock_director_class:
            mock_director = AsyncMock()
            mock_director.initialize = AsyncMock()
            mock_director_class.return_value = mock_director
            
            coordinator.directors = {uuid4(): AsyncMock()}
            coordinator._running = True
            
            await coordinator.scale_directors(3)
            
            assert len(coordinator.directors) == 3
            assert mock_director_class.call_count == 2
    
    @pytest.mark.asyncio
    async def test_scale_directors_down(self, coordinator):
        idle_director = AsyncMock()
        idle_director.shutdown = AsyncMock()
        idle_director.active_goals = {}
        
        busy_director = AsyncMock()
        busy_director.active_goals = {uuid4(): Mock(status="executing")}
        
        coordinator.directors = {
            uuid4(): idle_director,
            uuid4(): busy_director,
        }
        coordinator._running = True
        
        await coordinator.scale_directors(1)
        
        assert len(coordinator.directors) == 1
        idle_director.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_director_status(self, coordinator):
        mock_director = AsyncMock()
        mock_director.monitor_swarm = AsyncMock(return_value={
            "total_sub_orchestrators": 3,
            "idle_sub_orchestrators": 1,
        })
        director_id = uuid4()
        coordinator.directors[director_id] = mock_director
        
        statuses = await coordinator.get_director_status()
        
        assert len(statuses) == 1
        assert statuses[0]["director_id"] == str(director_id)
        assert statuses[0]["total_sub_orchestrators"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])