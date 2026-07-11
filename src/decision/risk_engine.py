"""risk_engine.py

Core risk engine for assessing and managing decision risks.
Quantifies risk, confidence, and uncertainty in decisions.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

if TYPE_CHECKING:
    from src.decision.decision_engine import DecisionContext, DecisionOption

logger = get_logger(__name__)


class RiskLevel(str, Enum):
    """Risk levels."""
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, Enum):
    """Categories of risk."""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    REPUTATIONAL = "reputational"
    TECHNICAL = "technical"
    TEMPORAL = "temporal"


@dataclass
class RiskFactor:
    """A specific risk factor."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: RiskCategory = RiskCategory.OPERATIONAL
    description: str = ""
    probability: float = 0.5  # 0.0 to 1.0
    impact: float = 0.5  # 0.0 to 1.0
    risk_score: float = 0.0  # probability * impact
    mitigation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.risk_score = self.probability * self.impact
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "description": self.description,
            "probability": self.probability,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "mitigation": self.mitigation,
            "metadata": self.metadata,
        }


@dataclass
class RiskAssessment:
    """A comprehensive risk assessment."""
    option_id: str
    overall_risk: float  # 0.0 to 1.0
    risk_level: RiskLevel
    risk_factors: List[RiskFactor] = field(default_factory=list)
    confidence: float = 0.5
    uncertainty: float = 0.5
    expected_loss: float = 0.0
    mitigation_recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "overall_risk": self.overall_risk,
            "risk_level": self.risk_level.value,
            "risk_factors": [rf.to_dict() for rf in self.risk_factors],
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "expected_loss": self.expected_loss,
            "mitigation_recommendations": self.mitigation_recommendations,
            "metadata": self.metadata,
        }


class RiskEngine:
    """Core risk engine for decision risk assessment."""
    
    def __init__(self):
        self.risk_thresholds = {
            RiskLevel.NEGLIGIBLE: 0.1,
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 0.9,
        }
        logger.info("RiskEngine initialized")
    
    def assess_risk(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        """Assess the risk of a decision option."""
        logger.info(f"Assessing risk for option: {option.description}")
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(option, context)
        
        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(risk_factors)
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_risk)
        
        # Calculate confidence
        confidence = self._calculate_confidence(option, risk_factors)
        
        # Calculate uncertainty
        uncertainty = self._calculate_uncertainty(risk_factors)
        
        # Calculate expected loss
        expected_loss = self._calculate_expected_loss(risk_factors)
        
        # Generate mitigation recommendations
        mitigation = self._generate_mitigation_recommendations(risk_factors)
        
        assessment = RiskAssessment(
            option_id=option.id,
            overall_risk=overall_risk,
            risk_level=risk_level,
            risk_factors=risk_factors,
            confidence=confidence,
            uncertainty=uncertainty,
            expected_loss=expected_loss,
            mitigation_recommendations=mitigation,
        )
        
        return assessment.to_dict()
    
    def _identify_risk_factors(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> List[RiskFactor]:
        """Identify specific risk factors for an option."""
        factors = []
        
        # Financial risk
        if option.cost.get("financial", 0) > 1000:
            factors.append(RiskFactor(
                category=RiskCategory.FINANCIAL,
                description="High financial cost",
                probability=0.7,
                impact=0.6,
                mitigation="Consider phased implementation to spread costs",
            ))
        
        # Operational risk
        action_type = option.action.get("type", "")
        if action_type in ["full_commitment", "innovate"]:
            factors.append(RiskFactor(
                category=RiskCategory.OPERATIONAL,
                description="Complex implementation",
                probability=0.5,
                impact=0.7,
                mitigation="Develop detailed implementation plan",
            ))
        
        # Strategic risk
        if context.time_horizon == "long":
            factors.append(RiskFactor(
                category=RiskCategory.STRATEGIC,
                description="Long-term uncertainty",
                probability=0.6,
                impact=0.5,
                mitigation="Include review points to adjust strategy",
            ))
        
        # Technical risk
        if action_type in ["innovate", "rapid"]:
            factors.append(RiskFactor(
                category=RiskCategory.TECHNICAL,
                description="Technical complexity",
                probability=0.4,
                impact=0.6,
                mitigation="Conduct technical feasibility study",
            ))
        
        # Temporal risk
        if option.drawbacks:
            for drawback in option.drawbacks:
                if "time" in drawback.lower() or "delay" in drawback.lower():
                    factors.append(RiskFactor(
                        category=RiskCategory.TEMPORAL,
                        description=drawback,
                        probability=0.5,
                        impact=0.4,
                        mitigation="Build buffer into timeline",
                    ))
                    break
        
        return factors
    
    def _calculate_overall_risk(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate overall risk from risk factors."""
        if not risk_factors:
            return 0.3  # Default moderate risk
        
        # Weighted average of risk scores
        total_weight = len(risk_factors)
        weighted_risk = sum(rf.risk_score for rf in risk_factors) / total_weight
        
        # Adjust for number of factors (more factors = higher risk)
        factor_multiplier = 1.0 + (len(risk_factors) - 1) * 0.1
        
        return min(1.0, weighted_risk * factor_multiplier)
    
    def _determine_risk_level(self, overall_risk: float) -> RiskLevel:
        """Determine risk level from overall risk score."""
        for level, threshold in sorted(self.risk_thresholds.items(), key=lambda x: x[1]):
            if overall_risk <= threshold:
                return level
        return RiskLevel.CRITICAL
    
    def _calculate_confidence(
        self,
        option: DecisionOption,
        risk_factors: List[RiskFactor],
    ) -> float:
        """Calculate confidence in the risk assessment."""
        # Base confidence from option
        base_confidence = option.confidence
        
        # Reduce confidence based on number of risk factors
        factor_penalty = min(0.3, len(risk_factors) * 0.05)
        
        return max(0.0, min(1.0, base_confidence - factor_penalty))
    
    def _calculate_uncertainty(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate uncertainty in the risk assessment."""
        if not risk_factors:
            return 0.3
        
        # Uncertainty based on variance in risk scores
        if len(risk_factors) < 2:
            return 0.4
        
        scores = [rf.risk_score for rf in risk_factors]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        
        return min(1.0, variance * 2)
    
    def _calculate_expected_loss(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate expected loss from risk factors."""
        # Sum of (probability * impact * cost_factor)
        total_loss = 0.0
        for rf in risk_factors:
            # Assume cost factor of 1.0 for now
            total_loss += rf.probability * rf.impact * 1.0
        
        return min(1.0, total_loss / len(risk_factors) if risk_factors else 0.0)
    
    def _generate_mitigation_recommendations(
        self,
        risk_factors: List[RiskFactor],
    ) -> List[str]:
        """Generate mitigation recommendations."""
        recommendations = []
        
        # Collect existing mitigations
        for rf in risk_factors:
            if rf.mitigation:
                recommendations.append(rf.mitigation)
        
        # Add general recommendations based on risk level
        if risk_factors:
            max_risk = max(rf.risk_score for rf in risk_factors)
            if max_risk > 0.7:
                recommendations.append("Consider developing contingency plans")
                recommendations.append("Monitor risk indicators closely")
        
        return list(set(recommendations))
    
    def compare_risks(
        self,
        assessments: List[RiskAssessment],
    ) -> Dict[str, Any]:
        """Compare risk assessments across options."""
        if not assessments:
            return {}
        
        comparison = {
            "total_assessments": len(assessments),
            "risk_levels": {},
            "average_risk": sum(a.overall_risk for a in assessments) / len(assessments),
            "highest_risk": max(a.overall_risk for a in assessments),
            "lowest_risk": min(a.overall_risk for a in assessments),
        }
        
        # Count by risk level
        for assessment in assessments:
            level = assessment.risk_level.value
            comparison["risk_levels"][level] = comparison["risk_levels"].get(level, 0) + 1
        
        return comparison
