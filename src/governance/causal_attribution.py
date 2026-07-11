"""causal_attribution.py

Phase 16H: Causal Attribution

Attributes outcomes to their causes.
Analyzes:
- Which factors caused success/failure
- Causal chains
- Counterfactual analysis
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class CausalStrength(str, Enum):
    """Strength of causal relationship."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


@dataclass
class CausalFactor:
    """A factor that contributed to an outcome."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    factor_name: str = ""
    factor_type: str = ""  # decision, context, external, etc.
    influence_direction: str = ""  # positive, negative
    strength: CausalStrength = CausalStrength.MODERATE
    confidence: float = 0.5
    description: str = ""
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "factor_name": self.factor_name,
            "factor_type": self.factor_type,
            "influence_direction": self.influence_direction,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "description": self.description,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass
class CausalAttribution:
    """Causal analysis of an outcome."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    outcome: Dict[str, Any] = field(default_factory=dict)
    causal_factors: List[CausalFactor] = field(default_factory=list)
    causal_chain: List[str] = field(default_factory=list)
    primary_cause: Optional[str] = None
    counterfactuals: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "outcome": self.outcome,
            "causal_factors": [f.to_dict() for f in self.causal_factors],
            "causal_chain": self.causal_chain,
            "primary_cause": self.primary_cause,
            "counterfactuals": self.counterfactuals,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class CausalAttributor:
    """Analyzes causal relationships in decision outcomes."""
    
    def __init__(self):
        self.attributions: Dict[str, CausalAttribution] = {}
        self.attributions_by_decision: Dict[str, str] = {}  # decision_id -> attribution_id
        logger.info("CausalAttributor initialized")
    
    def attribute_outcome(
        self,
        decision_data: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> CausalAttribution:
        """Attribute an outcome to its causes."""
        decision_id = decision_data.get("id", "")
        
        attribution = CausalAttribution(
            decision_id=decision_id,
            outcome=outcome,
        )
        
        # Identify causal factors
        attribution.causal_factors = self._identify_causal_factors(decision_data, outcome)
        
        # Build causal chain
        attribution.causal_chain = self._build_causal_chain(decision_data, outcome)
        
        # Identify primary cause
        attribution.primary_cause = self._identify_primary_cause(attribution.causal_factors)
        
        # Generate counterfactuals
        attribution.counterfactuals = self._generate_counterfactuals(decision_data, outcome)
        
        # Calculate confidence
        attribution.confidence = self._calculate_confidence(attribution)
        
        # Store attribution
        self.attributions[attribution.id] = attribution
        self.attributions_by_decision[decision_id] = attribution.id
        
        logger.info(f"Attributed outcome for decision {decision_id}")
        
        return attribution
    
    def _identify_causal_factors(
        self,
        decision_data: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> List[CausalFactor]:
        """Identify factors that causally contributed to the outcome."""
        factors = []
        
        success = outcome.get("success", False)
        
        # Analyze decision context
        context = decision_data.get("context", {})
        
        # Risk tolerance as a factor
        risk_tolerance = context.get("risk_tolerance", 0.5)
        if risk_tolerance > 0.7 and not success:
            factors.append(CausalFactor(
                factor_name="High risk tolerance",
                factor_type="context",
                influence_direction="negative",
                strength=CausalStrength.MODERATE,
                confidence=0.6,
                description="High risk tolerance may have led to risky choices",
            ))
        elif risk_tolerance < 0.3 and success:
            factors.append(CausalFactor(
                factor_name="Low risk tolerance",
                factor_type="context",
                influence_direction="positive",
                strength=CausalStrength.MODERATE,
                confidence=0.6,
                description="Conservative approach contributed to success",
            ))
        
        # Analyze selected option
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            utility = selected.get("utility_score", 0.5)
            risk = selected.get("risk_score", 0.5)
            
            if utility > 0.7 and success:
                factors.append(CausalFactor(
                    factor_name="High utility option",
                    factor_type="decision",
                    influence_direction="positive",
                    strength=CausalStrength.STRONG,
                    confidence=0.8,
                    description="Selecting high-utility option contributed to success",
                ))
            
            if risk > 0.6 and not success:
                factors.append(CausalFactor(
                    factor_name="High risk option",
                    factor_type="decision",
                    influence_direction="negative",
                    strength=CausalStrength.STRONG,
                    confidence=0.8,
                    description="Selecting high-risk option contributed to failure",
                ))
        
        # Analyze resource availability
        resources = context.get("available_resources", {})
        if not resources and not success:
            factors.append(CausalFactor(
                factor_name="Insufficient resources",
                factor_type="context",
                influence_direction="negative",
                strength=CausalStrength.MODERATE,
                confidence=0.7,
                description="Lack of resources may have hindered success",
            ))
        
        return factors
    
    def _build_causal_chain(
        self,
        decision_data: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> List[str]:
        """Build a causal chain from decision to outcome."""
        chain = []
        
        # Start with decision context
        context = decision_data.get("context", {})
        chain.append(f"Decision made with context: {context.get('time_horizon', 'unknown')} time horizon")
        
        # Add option selection
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            chain.append(f"Selected option: {selected.get('description', 'unknown')}")
            chain.append(f"Option utility: {selected.get('utility_score', 0):.2f}")
            chain.append(f"Option risk: {selected.get('risk_score', 0):.2f}")
        
        # Add outcome
        success = outcome.get("success", False)
        chain.append(f"Outcome: {'success' if success else 'failure'}")
        
        return chain
    
    def _identify_primary_cause(self, factors: List[CausalFactor]) -> Optional[str]:
        """Identify the primary causal factor."""
        if not factors:
            return None
        
        # Find the strongest factor
        strength_order = {
            CausalStrength.STRONG: 4,
            CausalStrength.MODERATE: 3,
            CausalStrength.WEAK: 2,
            CausalStrength.SPECULATIVE: 1,
        }
        
        strongest = max(
            factors,
            key=lambda f: (strength_order.get(f.strength, 0), f.confidence)
        )
        
        return strongest.factor_name
    
    def _generate_counterfactuals(
        self,
        decision_data: Dict[str, Any],
        outcome: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate counterfactual scenarios."""
        counterfactuals = []
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        
        # Counterfactual: What if a different option was selected?
        for option in options:
            if option.get("id") != selected_id:
                counterfactuals.append({
                    "type": "alternative_option",
                    "description": f"What if {option.get('description', 'unknown')} was selected?",
                    "expected_utility": option.get("utility_score", 0),
                    "expected_risk": option.get("risk_score", 0),
                })
        
        # Counterfactual: What if risk tolerance was different?
        context = decision_data.get("context", {})
        current_risk = context.get("risk_tolerance", 0.5)
        
        if current_risk > 0.5:
            counterfactuals.append({
                "type": "different_risk_tolerance",
                "description": "What if risk tolerance was lower?",
                "hypothesis": "Might have selected a safer option",
            })
        elif current_risk < 0.5:
            counterfactuals.append({
                "type": "different_risk_tolerance",
                "description": "What if risk tolerance was higher?",
                "hypothesis": "Might have selected a higher-reward option",
            })
        
        return counterfactuals[:3]  # Limit to top 3
    
    def _calculate_confidence(self, attribution: CausalAttribution) -> float:
        """Calculate confidence in the causal attribution."""
        if not attribution.causal_factors:
            return 0.3
        
        # Average confidence of factors
        avg_factor_confidence = sum(f.confidence for f in attribution.causal_factors) / len(attribution.causal_factors)
        
        # Adjust based on number of factors
        factor_count_adjustment = min(1.0, len(attribution.causal_factors) / 3)
        
        return avg_factor_confidence * factor_count_adjustment
    
    def get_attribution(self, attribution_id: str) -> Optional[CausalAttribution]:
        """Get an attribution by ID."""
        return self.attributions.get(attribution_id)
    
    def get_attribution_by_decision(self, decision_id: str) -> Optional[CausalAttribution]:
        """Get attribution by decision ID."""
        attribution_id = self.attributions_by_decision.get(decision_id)
        if attribution_id:
            return self.attributions.get(attribution_id)
        return None
    
    def get_common_causes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most common causal factors across all decisions."""
        factor_counts = {}
        
        for attribution in self.attributions.values():
            for factor in attribution.causal_factors:
                key = factor.factor_name
                if key not in factor_counts:
                    factor_counts[key] = {
                        "factor_name": key,
                        "count": 0,
                        "avg_strength": 0,
                    }
                factor_counts[key]["count"] += 1
                factor_counts[key]["avg_strength"] += (
                    1 if factor.strength == CausalStrength.STRONG else
                    0.5 if factor.strength == CausalStrength.MODERATE else
                    0.25
                )
        
        # Calculate average strength
        for key in factor_counts:
            if factor_counts[key]["count"] > 0:
                factor_counts[key]["avg_strength"] /= factor_counts[key]["count"]
        
        # Sort by count
        sorted_factors = sorted(factor_counts.values(), key=lambda x: x["count"], reverse=True)
        
        return sorted_factors[:limit]
    
    def get_attribution_statistics(self) -> Dict[str, Any]:
        """Get statistics about causal attributions."""
        total_attributions = len(self.attributions)
        
        if total_attributions == 0:
            return {"total_attributions": 0}
        
        total_factors = sum(len(a.causal_factors) for a in self.attributions.values())
        avg_factors = total_factors / total_attributions
        
        avg_confidence = (
            sum(a.confidence for a in self.attributions.values()) / total_attributions
        )
        
        return {
            "total_attributions": total_attributions,
            "total_factors_identified": total_factors,
            "average_factors_per_attribution": avg_factors,
            "average_confidence": avg_confidence,
        }
