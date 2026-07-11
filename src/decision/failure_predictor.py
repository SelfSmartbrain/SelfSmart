"""failure_predictor.py

Predicts potential failure modes for decisions.
Identifies and analyzes failure scenarios.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.decision_engine import DecisionOption, DecisionContext

logger = get_logger(__name__)


class FailureMode(str, Enum):
    """Types of failure modes."""
    RESOURCE = "resource"
    TECHNICAL = "technical"
    HUMAN = "human"
    EXTERNAL = "external"
    TIMING = "timing"
    QUALITY = "quality"


class FailureSeverity(str, Enum):
    """Severity levels for failures."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class FailureScenario:
    """A potential failure scenario."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: FailureMode = FailureMode.TECHNICAL
    description: str = ""
    probability: float = 0.5
    severity: FailureSeverity = FailureSeverity.MODERATE
    impact: float = 0.5
    detectability: float = 0.5  # How easy to detect
    mitigation: Optional[str] = None
    contingency: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def risk_priority_number(self) -> float:
        """Calculate Risk Priority Number (RPN)."""
        severity_score = {
            FailureSeverity.MINOR: 1,
            FailureSeverity.MODERATE: 5,
            FailureSeverity.MAJOR: 8,
            FailureSeverity.CRITICAL: 10,
        }
        return self.probability * 10 * severity_score[self.severity] * (1.0 - self.detectability)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "description": self.description,
            "probability": self.probability,
            "severity": self.severity.value,
            "impact": self.impact,
            "detectability": self.detectability,
            "mitigation": self.mitigation,
            "contingency": self.contingency,
            "rpn": self.risk_priority_number(),
            "metadata": self.metadata,
        }


@dataclass
class FailureAnalysis:
    """Analysis of potential failures for a decision."""
    option_id: str
    failure_scenarios: List[FailureScenario] = field(default_factory=list)
    overall_failure_probability: float = 0.0
    critical_failures: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "failure_scenarios": [fs.to_dict() for fs in self.failure_scenarios],
            "overall_failure_probability": self.overall_failure_probability,
            "critical_failures": self.critical_failures,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class FailurePredictor:
    """Predicts potential failure modes for decisions."""
    
    def __init__(self):
        self.failure_patterns: Dict[str, List[FailureScenario]] = {}
        logger.info("FailurePredictor initialized")
    
    def analyze_failures(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> FailureAnalysis:
        """Analyze potential failure modes for a decision option."""
        logger.info(f"Analyzing failures for option: {option.description}")
        
        # Identify failure scenarios
        scenarios = self._identify_failure_scenarios(option, context)
        
        # Calculate overall failure probability
        overall_prob = self._calculate_overall_failure_probability(scenarios)
        
        # Identify critical failures
        critical = self._identify_critical_failures(scenarios)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(scenarios)
        
        analysis = FailureAnalysis(
            option_id=option.id,
            failure_scenarios=scenarios,
            overall_failure_probability=overall_prob,
            critical_failures=critical,
            recommendations=recommendations,
        )
        
        return analysis
    
    def _identify_failure_scenarios(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> List[FailureScenario]:
        """Identify potential failure scenarios."""
        scenarios = []
        
        action_type = option.action.get("type", "")
        
        # Resource failure
        if option.cost.get("financial", 0) > 1000:
            scenarios.append(FailureScenario(
                mode=FailureMode.RESOURCE,
                description="Insufficient budget/resources",
                probability=0.4,
                severity=FailureSeverity.MAJOR,
                impact=0.7,
                detectability=0.8,
                mitigation="Secure additional funding",
                contingency="Scale down scope",
            ))
        
        # Technical failure
        if action_type in ["innovate", "full_commitment"]:
            scenarios.append(FailureScenario(
                mode=FailureMode.TECHNICAL,
                description="Technical implementation fails",
                probability=0.3,
                severity=FailureSeverity.CRITICAL,
                impact=0.9,
                detectability=0.6,
                mitigation="Conduct thorough testing",
                contingency="Fallback to alternative approach",
            ))
        
        # Timing failure
        if context.time_horizon == "short" and action_type in ["phased", "full_commitment"]:
            scenarios.append(FailureScenario(
                mode=FailureMode.TIMING,
                description="Timeline overrun",
                probability=0.5,
                severity=FailureSeverity.MODERATE,
                impact=0.5,
                detectability=0.7,
                mitigation="Build buffer into timeline",
                contingency="Extend deadline or reduce scope",
            ))
        
        # Quality failure
        if action_type in ["rapid", "innovate"]:
            scenarios.append(FailureScenario(
                mode=FailureMode.QUALITY,
                description="Quality standards not met",
                probability=0.3,
                severity=FailureSeverity.MODERATE,
                impact=0.6,
                detectability=0.8,
                mitigation="Implement quality gates",
                contingency="Additional testing phase",
            ))
        
        # External failure
        scenarios.append(FailureScenario(
            mode=FailureMode.EXTERNAL,
            description="External dependencies fail",
            probability=0.2,
            severity=FailureSeverity.MAJOR,
            impact=0.7,
            detectability=0.5,
            mitigation="Identify and monitor dependencies",
            contingency="Have backup suppliers/providers",
        ))
        
        # Human error
        if action_type in ["rapid", "full_commitment"]:
            scenarios.append(FailureScenario(
                mode=FailureMode.HUMAN,
                description="Human error in execution",
                probability=0.25,
                severity=FailureSeverity.MODERATE,
                impact=0.4,
                detectability=0.6,
                mitigation="Provide training and clear procedures",
                contingency="Review and correction process",
            ))
        
        return scenarios
    
    def _calculate_overall_failure_probability(
        self,
        scenarios: List[FailureScenario],
    ) -> float:
        """Calculate overall probability of any failure occurring."""
        if not scenarios:
            return 0.0
        
        # Probability of at least one failure = 1 - P(no failures)
        no_failure_prob = 1.0
        for scenario in scenarios:
            no_failure_prob *= (1.0 - scenario.probability)
        
        return 1.0 - no_failure_prob
    
    def _identify_critical_failures(
        self,
        scenarios: List[FailureScenario],
    ) -> List[str]:
        """Identify critical failure scenarios."""
        critical = []
        
        for scenario in scenarios:
            if scenario.severity == FailureSeverity.CRITICAL:
                critical.append(scenario.description)
            elif scenario.risk_priority_number() > 50:
                critical.append(scenario.description)
        
        return critical
    
    def _generate_recommendations(
        self,
        scenarios: List[FailureScenario],
    ) -> List[str]:
        """Generate recommendations based on failure scenarios."""
        recommendations = []
        
        # Collect mitigations
        for scenario in scenarios:
            if scenario.mitigation:
                recommendations.append(scenario.mitigation)
        
        # Add general recommendations
        if scenarios:
            max_rpn = max(s.risk_priority_number() for s in scenarios)
            if max_rpn > 50:
                recommendations.append("Develop comprehensive contingency plans")
                recommendations.append("Implement early warning systems")
        
        return list(set(recommendations))
    
    def learn_from_failure(
        self,
        failure_description: str,
        actual_mode: FailureMode,
        predicted: bool,
    ) -> None:
        """Learn from an actual failure to improve predictions."""
        # In a real implementation, this would update the failure patterns
        logger.info(f"Learning from failure: {failure_description}")
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about failure predictions."""
        return {
            "patterns_tracked": len(self.failure_patterns),
            "total_scenarios": sum(len(scenarios) for scenarios in self.failure_patterns.values()),
        }
