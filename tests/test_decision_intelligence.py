"""test_decision_intelligence.py

Tests for Phase 15: Decision Intelligence & Strategic Agency.
"""

import pytest
from src.decision.decision_engine import DecisionEngine, DecisionContext, DecisionOption
from src.decision.option_generator import OptionGenerator
from src.decision.decision_evaluator import DecisionEvaluator
from src.decision.utility_functions import UtilityFunctions, UtilityFunction, UtilityType
from src.decision.reward_models import RewardModels, RewardModel, RewardType, RewardSignal
from src.decision.objective_engine import ObjectiveEngine, Objective, ObjectiveStatus, ObjectivePriority
from src.decision.strategy_engine import StrategyEngine, Strategy, StrategicGoal, TimeHorizon, StrategyStatus
from src.decision.strategic_planner import StrategicPlanner, Plan, PlanStatus
from src.decision.goal_optimizer import GoalOptimizer
from src.decision.scenario_generator import ScenarioGenerator, Scenario, ScenarioType
from src.decision.future_simulator import FutureSimulator, SimulationResult
from src.decision.outcome_predictor import OutcomePredictor, Prediction
from src.decision.risk_engine import RiskEngine, RiskLevel
from src.decision.uncertainty_model import UncertaintyModel, UncertaintyType
from src.decision.failure_predictor import FailurePredictor
from src.decision.decision_memory import DecisionMemory
from src.decision.strategy_memory import StrategyMemory
from src.decision.outcome_memory import OutcomeMemory
from src.decision.pareto_optimizer import ParetoOptimizer, Objective, Solution
from src.decision.tradeoff_engine import TradeoffEngine, TradeoffType
from src.decision.executive_agent import ExecutiveAgent, ExecutiveStatus
from src.decision.executive_council import ExecutiveCouncil, CouncilRole, VotingMethod


class TestDecisionEngine:
    """Tests for DecisionEngine."""
    
    def test_initialization(self):
        """Test DecisionEngine initialization."""
        engine = DecisionEngine()
        assert engine is not None
        assert len(engine.active_decisions) == 0
    
    def test_make_decision(self):
        """Test making a decision."""
        engine = DecisionEngine()
        context = DecisionContext(risk_tolerance=0.5)
        decision = engine.make_decision("Test query", context)
        
        assert decision is not None
        assert decision.query == "Test query"
        assert len(decision.options) > 0
        assert decision.selected_option_id is not None
        assert decision.status.value == "decided"
    
    def test_execute_decision(self):
        """Test executing a decision."""
        engine = DecisionEngine()
        decision = engine.make_decision("Test query", DecisionContext())
        
        result = engine.execute_decision(decision.id)
        assert result["status"] == "executed"
    
    def test_record_outcome(self):
        """Test recording decision outcome."""
        engine = DecisionEngine()
        decision = engine.make_decision("Test query", DecisionContext())
        
        outcome = {"success": True, "value": 100}
        engine.record_outcome(decision.id, outcome)
        
        assert decision.outcome == outcome


class TestOptionGenerator:
    """Tests for OptionGenerator."""
    
    def test_generate_options(self):
        """Test generating options."""
        generator = OptionGenerator()
        context = DecisionContext()
        options = generator.generate_options("Test query", context, num_options=3)
        
        assert len(options) == 3
        assert all(isinstance(opt, DecisionOption) for opt in options)
    
    def test_consecutive_options(self):
        """Test conservative option generation."""
        generator = OptionGenerator()
        context = DecisionContext()
        options = generator.generate_options("Test query", context, strategy="conservative")
        
        assert len(options) > 0


class TestDecisionEvaluator:
    """Tests for DecisionEvaluator."""
    
    def test_evaluate_option(self):
        """Test evaluating an option."""
        evaluator = DecisionEvaluator()
        option = DecisionOption(description="Test option")
        context = DecisionContext()
        
        evaluation = evaluator.evaluate_option(option, context)
        
        assert "utility_score" in evaluation
        assert "risk_score" in evaluation
        assert "confidence" in evaluation
        assert 0.0 <= evaluation["utility_score"] <= 1.0


class TestUtilityFunctions:
    """Tests for UtilityFunctions."""
    
    def test_initialization(self):
        """Test UtilityFunctions initialization."""
        utils = UtilityFunctions()
        assert len(utils.list_functions()) > 0
    
    def test_evaluate_function(self):
        """Test evaluating a utility function."""
        utils = UtilityFunctions()
        value = utils.evaluate("risk_neutral", 0.5)
        
        assert value >= 0.0
    
    def test_expected_utility(self):
        """Test expected utility calculation."""
        utils = UtilityFunctions()
        outcomes = [0.3, 0.5, 0.7]
        probabilities = [0.2, 0.5, 0.3]
        
        eu = utils.expected_utility("risk_neutral", outcomes, probabilities)
        assert eu >= 0.0


class TestRewardModels:
    """Tests for RewardModels."""
    
    def test_initialization(self):
        """Test RewardModels initialization."""
        models = RewardModels()
        assert len(models.list_models()) > 0
    
    def test_create_model(self):
        """Test creating a reward model."""
        models = RewardModels()
        model = models.create_model(
            name="Test Model",
            description="Test description",
            reward_type=RewardType.SCALAR,
            reward_signals=[],
        )
        
        assert model is not None
        assert model.name == " Test Model"


class TestObjectiveEngine:
    """Tests for ObjectiveEngine."""
    
    def test_initialization(self):
        """Test ObjectiveEngine initialization."""
        engine = ObjectiveEngine()
        assert len(engine.list_objectives()) == 0
    
    def test_create_objective(self):
        """Test creating an objective."""
        engine = ObjectiveEngine()
        objective = engine.create_objective(
            name="Test Objective",
            description="Test description",
            priority=ObjectivePriority.HIGH,
        )
        
        assert objective is not None
        assert objective.name == "Test Objective"
        assert objective.status == ObjectiveStatus.ACTIVE
    
    def test_update_progress(self):
        """Test updating objective progress."""
        engine = ObjectiveEngine()
        objective = engine.create_objective("Test", "Description", target_value=1.0)
        
        engine.update_progress(objective.id, 0.5)
        updated = engine.get_objective(objective.id)
        
        assert updated.progress == 0.5


class TestStrategyEngine:
    """Tests for StrategyEngine."""
    
    def test_initialization(self):
        """Test StrategyEngine initialization."""
        engine = StrategyEngine()
        assert len(engine.list_strategies()) == 0
    
    def test_create_strategy(self):
        """Test creating a strategy."""
        engine = StrategyEngine()
        strategy = engine.create_strategy(
            name="Test Strategy",
            description="Test description",
            time_horizon=TimeHorizon.MONTH,
        )
        
        assert strategy is not None
        assert strategy.name == "Test Strategy"
        assert strategy.status == StrategyStatus.DRAFT
    
    def test_activate_strategy(self):
        """Test activating a strategy."""
        engine = StrategyEngine()
        strategy = engine.create_strategy("Test", "Description")
        
        engine.activate_strategy(strategy.id)
        active = engine.get_active_strategy()
        
        assert active is not None
        assert active.status == StrategyStatus.ACTIVE


class TestStrategicPlanner:
    """Tests for StrategicPlanner."""
    
    def test_initialization(self):
        """Test StrategicPlanner initialization."""
        planner = StrategicPlanner()
        assert len(planner.list_plans()) == 0
    
    def test_create_plan(self):
        """Test creating a plan."""
        planner = StrategicPlanner()
        plan = planner.create_plan(
            name="Test Plan",
            description="Test description",
            time_horizon=TimeHorizon.MONTH,
        )
        
        assert plan is not None
        assert plan.name == "Test Plan"
        assert plan.status == PlanStatus.DRAFT


class TestGoalOptimizer:
    """Tests for GoalOptimizer."""
    
    def test_initialization(self):
        """Test GoalOptimizer initialization."""
        optimizer = GoalOptimizer()
        assert optimizer is not None
    
    def test_optimize_goals(self):
        """Test optimizing goals."""
        optimizer = GoalOptimizer()
        from src.decision.strategy_engine import StrategicGoal, ObjectivePriority
        
        goals = [
            StrategicGoal(description="Goal 1", priority=ObjectivePriority.HIGH, estimated_effort=10.0),
            StrategicGoal(description="Goal 2", priority=ObjectivePriority.MEDIUM, estimated_effort=20.0),
        ]
        
        result = optimizer.optimize_goals(goals, {"total_effort": 25.0})
        
        assert result is not None
        assert len(result.optimized_goals) > 0


class TestScenarioGenerator:
    """Tests for ScenarioGenerator."""
    
    def test_initialization(self):
        """Test ScenarioGenerator initialization."""
        generator = ScenarioGenerator()
        assert generator is not None
    
    def test_generate_scenarios(self):
        """Test generating scenarios."""
        generator = ScenarioGenerator()
        scenarios = generator.generate_scenarios({}, num_scenarios=3)
        
        assert len(scenarios) == 3
        assert all(isinstance(s, Scenario) for s in scenarios)


class TestFutureSimulator:
    """Tests for FutureSimulator."""
    
    def test_initialization(self):
        """Test FutureSimulator initialization."""
        simulator = FutureSimulator()
        assert simulator is not None
    
    def test_simulate(self):
        """Test running a simulation."""
        simulator = FutureSimulator()
        scenario = ScenarioGenerator().generate_scenarios({}, num_scenarios=1)[0]
        
        result = simulator.simulate(
            scenario=scenario,
            action={"type": "test"},
            initial_state={"var1": 0.5},
            time_steps=5,
        )
        
        assert result is not None
        assert result.scenario_id == scenario.id


class TestOutcomePredictor:
    """Tests for OutcomePredictor."""
    
    def test_initialization(self):
        """Test OutcomePredictor initialization."""
        predictor = OutcomePredictor()
        assert predictor is not None
    
    def test_predict_outcome(self):
        """Test predicting outcomes."""
        predictor = OutcomePredictor()
        prediction = predictor.predict_outcome(
            decision_id="test_id",
            action={"type": "test"},
            context={},
            num_scenarios=3,
        )
        
        assert prediction is not None
        assert prediction.decision_id == "test_id"


class TestRiskEngine:
    """Tests for RiskEngine."""
    
    def test_initialization(self):
        """Test RiskEngine initialization."""
        engine = RiskEngine()
        assert engine is not None
    
    def test_assess_risk(self):
        """Test risk assessment."""
        engine = RiskEngine()
        option = DecisionOption(description="Test option")
        context = DecisionContext()
        
        assessment = engine.assess_risk(option, context)
        
        assert "overall_risk" in assessment
        assert "risk_level" in assessment
        assert 0.0 <= assessment["overall_risk"] <= 1.0


class TestUncertaintyModel:
    """Tests for UncertaintyModel."""
    
    def test_initialization(self):
        """Test UncertaintyModel initialization."""
        model = UncertaintyModel()
        assert model is not None
    
    def test_estimate_uncertainty(self):
        """Test uncertainty estimation."""
        model = UncertaintyModel()
        estimate = model.estimate_uncertainty("test", [0.3, 0.5, 0.7])
        
        assert estimate is not None
        assert estimate.mean is not None
        assert estimate.std_dev is not None


class TestFailurePredictor:
    """Tests for FailurePredictor."""
    
    def test_initialization(self):
        """Test FailurePredictor initialization."""
        predictor = FailurePredictor()
        assert predictor is not None
    
    def test_analyze_failures(self):
        """Test failure analysis."""
        predictor = FailurePredictor()
        option = DecisionOption(description="Test option")
        context = DecisionContext()
        
        analysis = predictor.analyze_failures(option, context)
        
        assert analysis is not None
        assert analysis.option_id == option.id


class TestDecisionMemory:
    """Tests for DecisionMemory."""
    
    def test_initialization(self):
        """Test DecisionMemory initialization."""
        memory = DecisionMemory()
        assert memory is not None
    
    def test_store_decision(self):
        """Test storing a decision."""
        memory = DecisionMemory()
        decision = Decision(query="Test", context=DecisionContext())
        decision.selected_option_id = "opt_1"
        decision.status = "decided"
        
        record = memory.store_decision(decision)
        
        assert record is not None
        assert record.decision_id == decision.id


class TestStrategyMemory:
    """Tests for StrategyMemory."""
    
    def test_initialization(self):
        """Test StrategyMemory initialization."""
        memory = StrategyMemory()
        assert memory is not None
    
    def test_store_strategy(self):
        """Test storing a strategy."""
        memory = StrategyMemory()
        strategy = Strategy(name="Test", description="Description")
        
        record = memory.store_strategy(strategy)
        
        assert record is not None
        assert record.strategy_id == strategy.id


class TestOutcomeMemory:
    """Tests for OutcomeMemory."""
    
    def test_initialization(self):
        """Test OutcomeMemory initialization."""
        memory = OutcomeMemory()
        assert memory is not None
    
    def test_store_outcome(self):
        """Test storing an outcome."""
        memory = OutcomeMemory()
        record = memory.store_outcome(
            action_id="test_id",
            action_type="test",
            context={},
            result={"success": True},
        )
        
        assert record is not None
        assert record.action_id == "test_id"


class TestParetoOptimizer:
    """Tests for ParetoOptimizer."""
    
    def test_initialization(self):
        """Test ParetoOptimizer initialization."""
        optimizer = ParetoOptimizer()
        assert optimizer is not None
    
    def test_find_pareto_front(self):
        """Test finding Pareto front."""
        optimizer = ParetoOptimizer()
        
        from src.decision.pareto_optimizer import Objective, Solution
        
        optimizer.add_objective(Objective(name="cost", maximize=False))
        optimizer.add_objective(Objective(name="quality", maximize=True))
        
        optimizer.add_solution(Solution(id="s1", values={"cost": 0.3, "quality": 0.8}, metadata={}))
        optimizer.add_solution(Solution(id="s2", values={"cost": 0.5, "quality": 0.9}, metadata={}))
        
        pareto_front = optimizer.find_pareto_front()
        
        assert len(pareto_front) > 0


class TestTradeoffEngine:
    """Tests for TradeoffEngine."""
    
    def test_initialization(self):
        """Test TradeoffEngine initialization."""
        engine = TradeoffEngine()
        assert engine is not None
    
    def test_analyze_tradeoff(self):
        """Test tradeoff analysis."""
        engine = TradeoffEngine()
        tradeoff = engine.analyze_tradeoff(
            factor1="cost",
            factor2="quality",
            factor1_value=0.5,
            factor2_value=0.7,
        )
        
        assert tradeoff is not None
        assert tradeoff.factor1 == "cost"


class TestExecutiveAgent:
    """Tests for ExecutiveAgent."""
    
    def test_initialization(self):
        """Test ExecutiveAgent initialization."""
        agent = ExecutiveAgent()
        assert agent is not None
        assert agent.status == ExecutiveStatus.IDLE
    
    def test_make_decision(self):
        """Test agent making a decision."""
        agent = ExecutiveAgent()
        decision = agent.make_decision("Test query")
        
        assert decision is not None
        assert decision.query == "Test query"
    
    def test_add_objective(self):
        """Test adding an objective."""
        agent = ExecutiveAgent()
        objective = agent.add_objective("Test", "Description")
        
        assert objective is not None
        assert len(agent.active_objectives) == 1


class TestExecutiveCouncil:
    """Tests for ExecutiveCouncil."""
    
    def test_initialization(self):
        """Test ExecutiveCouncil initialization."""
        council = ExecutiveCouncil()
        assert council is not None
        assert len(council.list_members()) == 0
    
    def test_add_member(self):
        """Test adding a council member."""
        council = ExecutiveCouncil()
        member = council.add_member("Test Member", role=CouncilRole.MEMBER)
        
        assert member is not None
        assert len(council.list_members()) == 1
    
    def test_propose_decision(self):
        """Test proposing a decision."""
        council = ExecutiveCouncil()
        member = council.add_member("Test Member")
        
        decision = council.propose_decision("Test proposal", member.id)
        
        assert decision is not None
        assert decision.proposal == "Test proposal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
