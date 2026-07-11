"""tradeoff_engine.py

Analyzes and manages tradeoffs between competing objectives.
Helps understand the cost-benefit of different decisions.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.config.logging import get_logger

logger = get_logger(__name__)


class TradeoffType(str, Enum):
    """Types of tradeoffs."""
    COST_VS_QUALITY = "cost_vs_quality"
    SPEED_VS_ACCURACY = "speed_vs_accuracy"
    RISK_VS_REWARD = "risk_vs_reward"
    SHORT_TERM_VS_LONG_TERM = "short_term_vs_long_term"
    RESOURCE_VS_IMPACT = "resource_vs_impact"


@dataclass
class Tradeoff:
    """A tradeoff between two competing factors."""
    id: str
    type: TradeoffType
    factor1: str
    factor2: str
    factor1_value: float
    factor2_value: float
    tradeoff_curve: List[Tuple[float, float]] = field(default_factory=list)
    optimal_point: Optional[Tuple[float, float]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "factor1": self.factor1,
            "factor2": self.factor2,
            "factor1_value": self.factor1_value,
            "factor2_value": self.factor2_value,
            "tradeoff_curve": self.tradeoff_curve,
            "optimal_point": self.optimal_point,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class TradeoffAnalysis:
    """Analysis of tradeoffs for a decision."""
    decision_id: str
    tradeoffs: List[Tradeoff] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    sensitivity_analysis: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "tradeoffs": [t.to_dict() for t in self.tradeoffs],
            "recommendations": self.recommendations,
            "sensitivity_analysis": self.sensitivity_analysis,
            "metadata": self.metadata,
        }


class TradeoffEngine:
    """Analyzes and manages tradeoffs between competing objectives."""
    
    def __init__(self):
        self.tradeoffs: Dict[str, Tradeoff] = {}
        self.tradeoff_curves: Dict[TradeoffType, List[Tuple[float, float]]] = {}
        logger.info("TradeoffEngine initialized")
    
    def analyze_tradeoff(
        self,
        factor1: str,
        factor2: str,
        factor1_value: float,
        factor2_value: float,
        tradeoff_type: TradeoffType = TradeoffType.RESOURCE_VS_IMPACT,
    ) -> Tradeoff:
        """Analyze a tradeoff between two factors."""
        import uuid
        
        tradeoff = Tradeoff(
            id=str(uuid.uuid4()),
            type=tradeoff_type,
            factor1=factor1,
            factor2=factor2,
            factor1_value=factor1_value,
            factor2_value=factor2_value,
            tradeoff_curve=self._generate_tradeoff_curve(tradeoff_type),
            optimal_point=self._find_optimal_point(tradeoff_type),
            description=f"Tradeoff between {factor1} and {factor2}",
        )
        
        self.tradeoffs[tradeoff.id] = tradeoff
        logger.info(f"Analyzed tradeoff: {factor1} vs {factor2}")
        
        return tradeoff
    
    def _generate_tradeoff_curve(
        self,
        tradeoff_type: TradeoffType,
    ) -> List[Tuple[float, float]]:
        """Generate a tradeoff curve for a given type."""
        curve = []
        
        # Generate points along the curve
        for i in range(11):
            x = i / 10.0  # 0.0 to 1.0
            
            if tradeoff_type == TradeoffType.COST_VS_QUALITY:
                # Quality improves with cost but with diminishing returns
                y = 1.0 - (1.0 - x) ** 2  # Convex curve
            elif tradeoff_type == TradeoffType.SPEED_VS_ACCURACY:
                # Accuracy decreases with speed
                y = 1.0 - x * 0.5  # Linear decrease
            elif tradeoff_type == TradeoffType.RISK_VS_REWARD:
                # Reward increases with risk but with diminishing returns
                y = x ** 0.5  # Concave curve
            elif tradeoff_type == TradeoffType.SHORT_TERM_VS_LONG_TERM:
                # Complex relationship
                y = 0.5 + 0.3 * (x - 0.5)  # Slight bias
            else:  # RESOURCE_VS_IMPACT
                # Impact increases with resources but with diminishing returns
                y = 1.0 - (1.0 - x) ** 1.5
            
            curve.append((x, y))
        
        return curve
    
    def _find_optimal_point(
        self,
        tradeoff_type: TradeoffType,
    ) -> Optional[Tuple[float, float]]:
        """Find the optimal point on the tradeoff curve."""
        curve = self._generate_tradeoff_curve(tradeoff_type)
        
        # Simple heuristic: find point closest to (1, 1) (ideal)
        best_point = None
        best_distance = float("inf")
        
        for x, y in curve:
            dist = ((1.0 - x) ** 2 + (1.0 - y) ** 2) ** 0.5
            if dist < best_distance:
                best_distance = dist
                best_point = (x, y)
        
        return best_point
    
    def analyze_decision_tradeoffs(
        self,
        decision_id: str,
        factors: Dict[str, float],
    ) -> TradeoffAnalysis:
        """Analyze all tradeoffs for a decision."""
        tradeoffs = []
        factor_names = list(factors.keys())
        
        # Analyze tradeoffs between all pairs of factors
        for i in range(len(factor_names)):
            for j in range(i + 1, len(factor_names)):
                factor1 = factor_names[i]
                factor2 = factor_names[j]
                
                tradeoff = self.analyze_tradeoff(
                    factor1=factor1,
                    factor2=factor2,
                    factor1_value=factors[factor1],
                    factor2_value=factors[factor2],
                )
                tradeoffs.append(tradeoff)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(tradeoffs)
        
        # Perform sensitivity analysis
        sensitivity = self._perform_sensitivity_analysis(factors)
        
        analysis = TradeoffAnalysis(
            decision_id=decision_id,
            tradeoffs=tradeoffs,
            recommendations=recommendations,
            sensitivity_analysis=sensitivity,
        )
        
        return analysis
    
    def _generate_recommendations(self, tradeoffs: List[Tradeoff]) -> List[str]:
        """Generate recommendations based on tradeoffs."""
        recommendations = []
        
        for tradeoff in tradeoffs:
            if tradeoff.optimal_point:
                opt_x, opt_y = tradeoff.optimal_point
                current_x = tradeoff.factor1_value
                current_y = tradeoff.factor2_value
                
                # Check if current point is far from optimal
                distance = ((opt_x - current_x) ** 2 + (opt_y - current_y) ** 2) ** 0.5
                
                if distance > 0.3:
                    recommendations.append(
                        f"Consider adjusting {tradeoff.factor1} and {tradeoff.factor2} "
                        f"toward optimal point ({opt_x:.2f}, {opt_y:.2f})"
                    )
        
        if not recommendations:
            recommendations.append("Current factor values appear well-balanced")
        
        return recommendations
    
    def _perform_sensitivity_analysis(
        self,
        factors: Dict[str, float],
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis on factors."""
        sensitivity = {}
        
        for factor_name, factor_value in factors.items():
            # Test small perturbations
            perturbations = [-0.1, -0.05, 0.05, 0.1]
            sensitivities = []
            
            for perturbation in perturbations:
                new_value = max(0.0, min(1.0, factor_value + perturbation))
                # In a real implementation, would recalculate objective
                # For now, use simple heuristic
                sensitivity_score = abs(perturbation)
                sensitivities.append(sensitivity_score)
            
            sensitivity[factor_name] = {
                "current_value": factor_value,
                "average_sensitivity": sum(sensitivities) / len(sensitivities),
                "max_sensitivity": max(sensitivities),
            }
        
        return sensitivity
    
    def find_balanced_solution(
        self,
        tradeoffs: List[Tradeoff],
        preferences: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Find a balanced solution considering all tradeoffs."""
        if not tradeoffs:
            return {}
        
        if preferences is None:
            preferences = {}
        
        # Simple averaging approach
        factor_values = {}
        factor_counts = {}
        
        for tradeoff in tradeoffs:
            factor_values[tradeoff.factor1] = factor_values.get(tradeoff.factor1, 0.0) + tradeoff.factor1_value
            factor_counts[tradeoff.factor1] = factor_counts.get(tradeoff.factor1, 0) + 1
            
            factor_values[tradeoff.factor2] = factor_values.get(tradeoff.factor2, 0.0) + tradeoff.factor2_value
            factor_counts[tradeoff.factor2] = factor_counts.get(tradeoff.factor2, 0) + 1
        
        # Calculate averages
        balanced = {}
        for factor in factor_values:
            balanced[factor] = factor_values[factor] / factor_counts[factor]
        
        # Apply preferences
        for factor, preference in preferences.items():
            if factor in balanced:
                balanced[factor] = (balanced[factor] + preference) / 2.0
        
        return balanced
    
    def get_tradeoff_summary(self) -> Dict[str, Any]:
        """Get a summary of all tradeoffs."""
        if not self.tradeoffs:
            return {"total_tradeoffs": 0}
        
        return {
            "total_tradeoffs": len(self.tradeoffs),
            "by_type": {
                ttype.value: sum(1 for t in self.tradeoffs.values() if t.type == ttype)
                for ttype in TradeoffType
            },
        }
