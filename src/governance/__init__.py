"""governance

Phase 16: Meta-Cognitive Governance & Self-Evolving Decision Systems

Transforms ModelX from a decision maker into a decision scientist.

Components:
- Decision Audit Engine: Track decision reasoning, evidence, and outcomes
- Assumption Extraction: Identify hidden assumptions and beliefs
- Decision Pattern Mining: Discover recurring success/failure patterns
- Governance Framework: Enforce policies and constraints
- Executive Review Board: Strategic review of major decisions
- Decision Evolution Engine: Improve decision-making over time
- Decision Fitness Metrics: Measure decision quality
- Long-Term Outcome Tracking: Track outcomes over time
- Strategic Governance Memory: Store historic decisions and lessons
"""

from __future__ import annotations

# 16A: Decision Audit Engine
from src.governance.decision_auditor import DecisionAuditor
from src.governance.decision_trace import DecisionTrace, DecisionTraceManager
from src.governance.explanation_engine import ExplanationEngine, DecisionExplanation

# 16B: Assumption Extraction
from src.governance.assumption_detector import AssumptionDetector, Assumption
from src.governance.belief_extractor import BeliefExtractor, Belief
from src.governance.premise_analyzer import PremiseAnalyzer, Premise

# 16C: Decision Pattern Mining
from src.governance.decision_pattern_miner import DecisionPatternMiner, DecisionPattern
from src.governance.success_pattern_detector import SuccessPatternDetector, SuccessPattern
from src.governance.failure_pattern_detector import FailurePatternDetector, FailurePattern

# 16D: Governance Framework
from src.governance.governance_engine import GovernanceEngine, GovernanceResult
from src.governance.policy_manager import PolicyManager, Policy
from src.governance.constraint_system import ConstraintSystem, Constraint

# 16E: Executive Review Board
from src.governance.review_board import ReviewBoard, DecisionReview
from src.governance.strategic_review import StrategicReviewer, StrategicReview

# 16F: Decision Evolution Engine
from src.governance.decision_evolution import DecisionEvolutionEngine, EvolutionProposal
from src.governance.strategy_mutator import StrategyMutator, StrategyMutation
from src.governance.policy_optimizer import PolicyOptimizer, PolicyOptimization

# 16G: Decision Fitness Metrics
from src.governance.decision_fitness import DecisionFitnessCalculator, DecisionFitness
from src.governance.decision_benchmark import DecisionBenchmark, BenchmarkResult

# 16H: Long-Term Outcome Tracking
from src.governance.outcome_tracker import OutcomeTracker, OutcomeTracking
from src.governance.outcome_validator import OutcomeValidator, OutcomeValidation
from src.governance.causal_attribution import CausalAttributor, CausalAttribution

# 16I: Strategic Governance Memory
from src.governance.governance_memory import GovernanceMemory, GovernanceRecord
from src.governance.policy_memory import PolicyMemory, PolicyVersion
from src.governance.decision_archive import DecisionArchive, ArchivedDecision

__all__ = [
    # 16A: Decision Audit Engine
    "DecisionAuditor",
    "DecisionTrace",
    "DecisionTraceManager",
    "ExplanationEngine",
    "DecisionExplanation",
    
    # 16B: Assumption Extraction
    "AssumptionDetector",
    "Assumption",
    "BeliefExtractor",
    "Belief",
    "PremiseAnalyzer",
    "Premise",
    
    # 16C: Decision Pattern Mining
    "DecisionPatternMiner",
    "DecisionPattern",
    "SuccessPatternDetector",
    "SuccessPattern",
    "FailurePatternDetector",
    "FailurePattern",
    
    # 16D: Governance Framework
    "GovernanceEngine",
    "GovernanceResult",
    "PolicyManager",
    "Policy",
    "ConstraintSystem",
    "Constraint",
    
    # 16E: Executive Review Board
    "ReviewBoard",
    "DecisionReview",
    "StrategicReviewer",
    "StrategicReview",
    
    # 16F: Decision Evolution Engine
    "DecisionEvolutionEngine",
    "EvolutionProposal",
    "StrategyMutator",
    "StrategyMutation",
    "PolicyOptimizer",
    "PolicyOptimization",
    
    # 16G: Decision Fitness Metrics
    "DecisionFitnessCalculator",
    "DecisionFitness",
    "DecisionBenchmark",
    "BenchmarkResult",
    
    # 16H: Long-Term Outcome Tracking
    "OutcomeTracker",
    "OutcomeTracking",
    "OutcomeValidator",
    "OutcomeValidation",
    "CausalAttributor",
    "CausalAttribution",
    
    # 16I: Strategic Governance Memory
    "GovernanceMemory",
    "GovernanceRecord",
    "PolicyMemory",
    "PolicyVersion",
    "DecisionArchive",
    "ArchivedDecision",
]
