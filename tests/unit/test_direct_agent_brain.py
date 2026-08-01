"""
Unit tests for DirectAgentBrain - Embedded Multi-Agent Brain Engine
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
import json

from src.agents.direct_agent_brain import (
    DirectAgentBrain,
    MultiAgentSwarm,
    BrainState,
    AgentResult,
    AgentRole,
)


class TestAgentRole:
    """Test AgentRole enum"""
    
    def test_agent_roles(self):
        assert AgentRole.PLANNER.value == "planner"
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.EVALUATOR.value == "evaluator"
        assert AgentRole.SAFETY_GATE.value == "safety_gate"


class TestBrainState:
    """Test BrainState dataclass"""
    
    def test_default_state(self):
        state = BrainState(objective="Test objective")
        
        assert state.objective == "Test objective"
        assert state.current_step == 0
        assert state.max_steps == 10
        assert state.plan == []
        assert state.research_findings == []
        assert state.code_patches == []
        assert state.evaluation_results == []
        assert state.safety_checks == []
        assert state.final_output is None
        assert state.errors == []
        assert state.metadata == {}
    
    def test_custom_state(self):
        state = BrainState(
            objective="Custom",
            max_steps=5,
            metadata={"key": "value"},
        )
        
        assert state.max_steps == 5
        assert state.metadata == {"key": "value"}


class TestAgentResult:
    """Test AgentResult dataclass"""
    
    def test_success_result(self):
        result = AgentResult(
            agent_role=AgentRole.PLANNER,
            success=True,
            output={"plan": []},
            reasoning="Success",
            confidence=0.9,
        )
        
        assert result.success is True
        assert result.confidence == 0.9
    
    def test_failure_result(self):
        result = AgentResult(
            agent_role=AgentRole.CODER,
            success=False,
            output=None,
            reasoning="Error occurred",
            confidence=0.0,
        )
        
        assert result.success is False
        assert result.confidence == 0.0


class TestDirectAgentBrain:
    """Test DirectAgentBrain"""
    
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.generate = Mock(return_value='{"test": "response"}')
        return engine
    
    def test_init(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        
        assert brain.engine == mock_engine
        assert len(brain._agents) == 5
        assert AgentRole.PLANNER in brain._agents
        assert AgentRole.RESEARCHER in brain._agents
        assert AgentRole.CODER in brain._agents
        assert AgentRole.EVALUATOR in brain._agents
        assert AgentRole.SAFETY_GATE in brain._agents
    
    def test_step_initializes_state(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        state = brain.step("Test objective")
        
        assert isinstance(state, BrainState)
        assert state.objective == "Test objective"
        assert state.current_step > 0
    
    def test_planner_node(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        mock_engine.generate.return_value = json.dumps([
            {"step_id": "1", "description": "Step 1", "agent": "researcher", "dependencies": [], "success_criteria": "Done"}
        ])
        
        state = BrainState(objective="Test")
        result = brain._planner_node(state)
        
        assert "plan" in result
        assert len(result["plan"]) == 1
        assert state.plan == result["plan"]
    
    def test_planner_node_fallback(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        # Return invalid JSON to trigger fallback
        mock_engine.generate.return_value = "not valid json"
        
        state = BrainState(objective="Test")
        result = brain._planner_node(state)
        
        assert "plan" in result
        assert result.get("fallback") is True
        assert len(state.plan) == 3
    
    def test_researcher_node(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        mock_engine.generate.return_value = json.dumps({
            "files_to_examine": ["src/"],
            "key_concepts": ["test"],
            "dependencies": [],
            "risks": [],
            "recommendations": [],
        })
        
        state = BrainState(objective="Test", plan=[{"step_id": "1", "agent": "researcher"}])
        result = brain._researcher_node(state)
        
        assert "files_to_examine" in result
        assert len(state.research_findings) == 1
    
    def test_coder_node(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        mock_engine.generate.return_value = json.dumps({
            "files": [{"path": "test.py", "content": "print('hello')"}],
            "explanation": "Test",
            "tests": ["test"],
        })
        
        state = BrainState(objective="Test")
        state.research_findings = [{"files_to_examine": ["src/"]}]
        state.plan = [{"step_id": "1"}]
        
        result = brain._coder_node(state)
        
        assert "files" in result
        assert len(state.code_patches) == 1
    
    def test_evaluator_node(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        mock_engine.generate.return_value = json.dumps({
            "score": 0.8,
            "criteria_met": ["test"],
            "criteria_failed": [],
            "issues": [],
            "suggestions": [],
            "passes": True,
        })
        
        state = BrainState(objective="Test")
        state.code_patches = [{"files": []}]
        state.plan = [{"step_id": "1"}]
        
        result = brain._evaluator_node(state)
        
        assert result["score"] == 0.8
        assert result["passes"] is True
        assert len(state.evaluation_results) == 1
    
    def test_safety_gate_node(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        mock_engine.generate.return_value = json.dumps({
            "safe": True,
            "violations": [],
            "warnings": [],
            "recommended_action": "allow",
        })
        
        state = BrainState(objective="Test")
        state.code_patches = [{"files": []}]
        state.evaluation_results = [{"score": 0.8}]
        
        result = brain._safety_gate_node(state)
        
        assert result["safe"] is True
        assert result["recommended_action"] == "allow"
        assert len(state.safety_checks) == 1
    
    def test_execute_agent_success(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        state = BrainState(objective="Test")
        brain._state = state
        
        result = brain._execute_agent(AgentRole.PLANNER)
        
        assert result.success is True
        assert result.agent_role == AgentRole.PLANNER
    
    def test_execute_agent_unknown_role(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        state = BrainState(objective="Test")
        brain._state = state
        
        # Patch agents to remove one
        brain._agents = {}
        
        result = brain._execute_agent(AgentRole.PLANNER)
        
        assert result.success is False
        assert "Unknown agent role" in result.reasoning
    
    def test_get_execution_history(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        state = brain.step("Test")
        
        history = brain.get_execution_history()
        
        assert len(history) == 5  # 5 agents
        assert all(isinstance(h, AgentResult) for h in history)
    
    def test_get_state(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        state = brain.step("Test")
        
        retrieved = brain.get_state()
        
        assert retrieved == state
    
    def test_reset(self, mock_engine):
        brain = DirectAgentBrain(mock_engine)
        brain.step("Test 1")
        brain.reset()
        
        assert brain._state is None
        assert brain._execution_history == []


class TestMultiAgentSwarm:
    """Test MultiAgentSwarm"""
    
    def test_init(self):
        swarm = MultiAgentSwarm(num_brains=3)
        
        assert swarm.num_brains == 3
        assert swarm._engines == []
        assert swarm._brains == []
    
    @patch('src.agents.direct_agent_brain.LocalWeightEngine')
    def test_initialize(self, mock_engine_class):
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        swarm = MultiAgentSwarm(num_brains=2)
        config = Mock()
        swarm.initialize(config)
        
        assert len(swarm._engines) == 2
        assert len(swarm._brains) == 2
        assert mock_engine.load_model.call_count == 2
        assert mock_engine.attach_lora.call_count == 2
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_solve_parallel(self, mock_executor_class):
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Mock futures
        mock_future1 = Mock()
        mock_future1.result.return_value = BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.7}})
        mock_future2 = Mock()
        mock_future2.result.return_value = BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.9}})
        
        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        
        # Mock as_completed
        import concurrent.futures
        original_as_completed = concurrent.futures.as_completed
        concurrent.futures.as_completed = lambda fs: [mock_future1, mock_future2]
        
        try:
            swarm = MultiAgentSwarm(num_brains=2)
            swarm._brains = [Mock(), Mock()]
            swarm._brains[0].step = Mock(return_value=BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.7}}))
            swarm._brains[1].step = Mock(return_value=BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.9}}))
            
            results = swarm.solve_parallel("Test objective")
            
            assert len(results) == 2
        finally:
            concurrent.futures.as_completed = original_as_completed
    
    def test_consensus(self):
        swarm = MultiAgentSwarm(num_brains=2)
        
        state1 = BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.7}})
        state2 = BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.9}})
        state3 = BrainState(objective="Test", metadata={"summary": {"evaluation_score": 0.5}})
        
        best = swarm.consensus([state1, state2, state3])
        
        assert best.metadata["summary"]["evaluation_score"] == 0.9
    
    def test_cleanup(self):
        swarm = MultiAgentSwarm(num_brains=2)
        mock_engine1 = Mock()
        mock_engine2 = Mock()
        swarm._engines = [mock_engine1, mock_engine2]
        swarm._brains = [Mock(), Mock()]
        
        swarm.cleanup()
        
        mock_engine1.unload.assert_called_once()
        mock_engine2.unload.assert_called_once()
        assert swarm._engines == []
        assert swarm._brains == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])