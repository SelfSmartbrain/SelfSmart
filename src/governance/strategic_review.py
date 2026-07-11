"""strategic_review.py

Phase 16E: Strategic Review

Provides strategic assessment of decisions.
Evaluates:
- Strategic alignment
- Long-term impact
- Resource implications
- Risk-reward balance
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class StrategicDimension(str, Enum):
    """Dimensions of strategic assessment."""
    ALIGNMENT = "alignment"
    IMPACT = "impact"
    FEASIBILITY = "feasibility"
    RISK_REWARD = "risk_reward"
    TIMING = "timing"
    RESOURCE_EFFICIENCY = "resource_efficiency"


@dataclass
class StrategicAssessment:
    """Assessment of a decision along strategic dimensions."""
    dimension: StrategicDimension
    score: float  # 0.0 to 1.0
    rationale: str = ""
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "rationale": self.rationale,
            "concerns": self.concerns,
            "recommendations": self.recommendations,
        }


@dataclass
class StrategicReview:
    """Strategic review of a decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    decision_query: str = ""
    overall_score: float = 0.0
    assessments: List[StrategicAssessment] = field(default_factory=list)
    strategic_fit: str = ""  # high, medium, low
    long_term_implications: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    final_recommendation: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "decision_query": self.decision_query,
            "overall_score": self.overall_score,
            "assessments": [a.to_dict() for a in self.assessments],
            "strategic_fit": self.strategic_fit,
            "long_term_implications": self.long_term_implications,
            "alternatives": self.alternatives,
            "final_recommendation": self.final_recommendation,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class StrategicReviewer:
    """Provides strategic review of decisions."""
    
    def __init__(self):
        self.reviews: Dict[str, StrategicReview] = {}
        self.strategic_objectives: List[str] = []
        logger.info("StrategicReviewer initialized")
    
    def set_strategic_objectives(self, objectives: List[str]) -> None:
        """Set the strategic objectives for assessment."""
        self.strategic_objectives = objectives
        logger.info(f"Set {len(objectives)} strategic objectives")
    
    def conduct_review(
        self,
        decision_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> StrategicReview:
        """Conduct a strategic review of a decision."""
        context = context or decision_data.get("context", {})
        
        review = StrategicReview(
            decision_id=decision_data.get("id", ""),
            decision_query=decision_data.get("query", ""),
        )
        
        # Assess all strategic dimensions
        review.assessments = [
            self._assess_alignment(decision_data, context),
            self._assess_impact(decision_data, context),
            self._assess_feasibility(decision_data, context),
            self._assess_risk_reward(decision_data, context),
            self._assess_timing(decision_data, context),
            self._assess_resource_efficiency(decision_data, context),
        ]
        
        # Calculate overall score
        review.overall_score = sum(a.score for a in review.assessments) / len(review.assessments)
        
        # Determine strategic fit
        review.strategic_fit = self._determine_strategic_fit(review.overall_score)
        
        # Analyze long-term implications
        review.long_term_implications = self._analyze_long_term_implications(decision_data, context)
        
        # Suggest alternatives
        review.alternatives = self._suggest_alternatives(decision_data)
        
        # Generate final recommendation
        review.final_recommendation = self._generate_recommendation(review)
        
        # Calculate confidence
        review.confidence = self._calculate_confidence(review)
        
        # Store review
        self.reviews[review.id] = review
        
        logger.info(f"Conducted strategic review for decision {review.decision_id}")
        
        return review
    
    def _assess_alignment(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess strategic alignment."""
        assessment = StrategicAssessment(dimension=StrategicDimension.ALIGNMENT)
        
        # Check alignment with strategic objectives
        query = decision_data.get("query", "").lower()
        objectives = [obj.lower() for obj in self.strategic_objectives]
        
        alignment_score = 0.5
        aligned_objectives = []
        
        for objective in objectives:
            if any(word in query for word in objective.split()):
                aligned_objectives.append(objective)
                alignment_score += 0.1
        
        assessment.score = min(1.0, alignment_score)
        assessment.rationale = f"Decision aligns with {len(aligned_objectives)} strategic objectives"
        
        if aligned_objectives:
            assessment.rationale += f": {', '.join(aligned_objectives[:2])}"
        else:
            assessment.concerns.append("No clear alignment with strategic objectives")
            assessment.recommendations.append("Consider how this decision supports strategic goals")
        
        return assessment
    
    def _assess_impact(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess strategic impact."""
        assessment = StrategicAssessment(dimension=StrategicDimension.IMPACT)
        
        # Analyze expected outcomes
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            benefits = selected.get("benefits", [])
            impact_score = min(1.0, len(benefits) * 0.2)
            assessment.score = impact_score
            assessment.rationale = f"Decision has {len(benefits)} expected benefits"
            
            if len(benefits) < 2:
                assessment.concerns.append("Limited strategic impact expected")
                assessment.recommendations.append("Consider higher-impact alternatives")
        else:
            assessment.score = 0.5
            assessment.rationale = "Unable to assess impact - no selected option"
        
        return assessment
    
    def _assess_feasibility(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess feasibility."""
        assessment = StrategicAssessment(dimension=StrategicDimension.FEASIBILITY)
        
        # Check resource availability
        resources = context.get("available_resources", {})
        constraints = context.get("constraints", [])
        
        feasibility_score = 0.8
        
        if len(constraints) > 5:
            feasibility_score -= 0.2
            assessment.concerns.append("Many constraints may affect feasibility")
        
        if not resources:
            feasibility_score -= 0.3
            assessment.concerns.append("No resources specified - feasibility uncertain")
            assessment.recommendations.append("Define required resources")
        
        assessment.score = max(0.0, feasibility_score)
        assessment.rationale = f"Feasibility assessment based on {len(constraints)} constraints and resource availability"
        
        return assessment
    
    def _assess_risk_reward(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess risk-reward balance."""
        assessment = StrategicAssessment(dimension=StrategicDimension.RISK_REWARD)
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            utility = selected.get("utility_score", 0.5)
            risk = selected.get("risk_score", 0.5)
            
            # Risk-reward ratio
            if risk > 0:
                ratio = utility / risk
            else:
                ratio = utility
            
            assessment.score = min(1.0, ratio)
            assessment.rationale = f"Risk-reward ratio: {ratio:.2f} (utility: {utility:.2f}, risk: {risk:.2f})"
            
            if risk > 0.7:
                assessment.concerns.append("High risk relative to reward")
                assessment.recommendations.append("Consider risk mitigation strategies")
        else:
            assessment.score = 0.5
            assessment.rationale = "Unable to assess risk-reward"
        
        return assessment
    
    def _assess_timing(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess timing."""
        assessment = StrategicAssessment(dimension=StrategicDimension.TIMING)
        
        time_horizon = context.get("time_horizon", "medium")
        
        # Simple timing assessment
        timing_scores = {
            "short": 0.7,
            "medium": 0.8,
            "long": 0.6,
        }
        
        assessment.score = timing_scores.get(time_horizon, 0.7)
        assessment.rationale = f"Time horizon: {time_horizon}"
        
        if time_horizon == "long":
            assessment.concerns.append("Long time horizon increases uncertainty")
            assessment.recommendations.append("Implement milestone checkpoints")
        
        return assessment
    
    def _assess_resource_efficiency(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> StrategicAssessment:
        """Assess resource efficiency."""
        assessment = StrategicAssessment(dimension=StrategicDimension.RESOURCE_EFFICIENCY)
        
        resources = context.get("available_resources", {})
        
        if resources:
            # Simple efficiency check - more resources with less constraints is better
            efficiency_score = min(1.0, len(resources) * 0.15)
            assessment.score = efficiency_score
            assessment.rationale = f"Resource efficiency based on {len(resources)} resource types"
        else:
            assessment.score = 0.5
            assessment.rationale = "No resource information available"
            assessment.recommendations.append("Specify resource requirements")
        
        return assessment
    
    def _determine_strategic_fit(self, overall_score: float) -> str:
        """Determine strategic fit level."""
        if overall_score >= 0.8:
            return "high"
        elif overall_score >= 0.6:
            return "medium"
        else:
            return "low"
    
    def _analyze_long_term_implications(
        self,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[str]:
        """Analyze long-term implications."""
        implications = []
        
        time_horizon = context.get("time_horizon", "medium")
        
        if time_horizon == "long":
            implications.append("Long-term commitment required")
            implications.append("May limit future flexibility")
            implications.append("Requires ongoing resource allocation")
        elif time_horizon == "medium":
            implications.append("Medium-term strategic commitment")
            implications.append("Balance between commitment and flexibility")
        else:
            implications.append("Short-term tactical decision")
            implications.append("Minimal long-term commitment")
        
        return implications
    
    def _suggest_alternatives(
        self,
        decision_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Suggest alternative approaches."""
        alternatives = []
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        
        for option in options:
            if option.get("id") != selected_id:
                alternatives.append({
                    "description": option.get("description", ""),
                    "utility_score": option.get("utility_score", 0),
                    "risk_score": option.get("risk_score", 0),
                    "rationale": "Alternative option with different risk-reward profile",
                })
        
        return alternatives[:3]  # Top 3 alternatives
    
    def _generate_recommendation(self, review: StrategicReview) -> str:
        """Generate final recommendation."""
        if review.strategic_fit == "high":
            return "Recommended - decision aligns well with strategic objectives"
        elif review.strategic_fit == "medium":
            return "Conditionally recommended - address concerns before proceeding"
        else:
            return "Not recommended - reconsider approach or objectives"
    
    def _calculate_confidence(self, review: StrategicReview) -> float:
        """Calculate confidence in the review."""
        # Confidence based on consistency of assessments
        scores = [a.score for a in review.assessments]
        
        if not scores:
            return 0.5
        
        variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
        confidence = max(0.0, 1.0 - variance)
        
        return confidence
    
    def get_review(self, review_id: str) -> Optional[StrategicReview]:
        """Get a review by ID."""
        return self.reviews.get(review_id)
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """Get statistics about strategic reviews."""
        total_reviews = len(self.reviews)
        
        if total_reviews == 0:
            return {"total_reviews": 0}
        
        avg_score = sum(r.overall_score for r in self.reviews.values()) / total_reviews
        
        by_fit = {
            fit: len([r for r in self.reviews.values() if r.strategic_fit == fit])
            for fit in ["high", "medium", "low"]
        }
        
        return {
            "total_reviews": total_reviews,
            "average_score": avg_score,
            "by_strategic_fit": by_fit,
        }
