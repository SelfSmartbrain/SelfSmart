"""explanation_engine.py

Phase 16A: Explanation Engine

Generates human-readable explanations for decisions.
Explains:
- Why a decision was made
- What evidence supported it
- What alternatives were considered
- What risks were assessed
- What assumptions were made
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.governance.decision_trace import DecisionTrace

logger = get_logger(__name__)


@dataclass
class DecisionExplanation:
    """A structured explanation of a decision."""
    decision_id: str = ""
    summary: str = ""
    reasoning_chain: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    risks_assessed: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    confidence_level: float = 0.0
    confidence_explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "summary": self.summary,
            "reasoning_chain": self.reasoning_chain,
            "key_factors": self.key_factors,
            "evidence": self.evidence,
            "alternatives_considered": self.alternatives_considered,
            "risks_assessed": self.risks_assessed,
            "assumptions": self.assumptions,
            "confidence_level": self.confidence_level,
            "confidence_explanation": self.confidence_explanation,
            "metadata": self.metadata,
        }
    
    def format_for_display(self) -> str:
        """Format the explanation for human display."""
        lines = [
            f"Decision: {self.decision_id}",
            f"\nSummary:\n{self.summary}",
            f"\nConfidence: {self.confidence_level:.1%}",
            f"({self.confidence_explanation})",
        ]
        
        if self.reasoning_chain:
            lines.append("\nReasoning Chain:")
            for i, step in enumerate(self.reasoning_chain, 1):
                lines.append(f"  {i}. {step}")
        
        if self.key_factors:
            lines.append("\nKey Factors:")
            for factor in self.key_factors:
                lines.append(f"  - {factor}")
        
        if self.evidence:
            lines.append("\nEvidence:")
            for evidence in self.evidence:
                lines.append(f"  - {evidence}")
        
        if self.assumptions:
            lines.append("\nAssumptions:")
            for assumption in self.assumptions:
                lines.append(f"  - {assumption}")
        
        if self.alternatives_considered:
            lines.append("\nAlternatives Considered:")
            for alt in self.alternatives_considered:
                lines.append(f"  - {alt.get('description', 'Unknown')}: {alt.get('reason', '')}")
        
        if self.risks_assessed:
            lines.append("\nRisks Assessed:")
            for risk in self.risks_assessed:
                lines.append(f"  - {risk.get('type', 'Unknown')}: {risk.get('level', 'Unknown')}")
        
        return "\n".join(lines)


class ExplanationEngine:
    """Generates explanations for decisions."""
    
    def __init__(self):
        logger.info("ExplanationEngine initialized")
    
    def generate_explanation(
        self,
        decision_id: str,
        decision_data: Dict[str, Any],
        trace: Optional[DecisionTrace] = None,
    ) -> DecisionExplanation:
        """Generate a comprehensive explanation for a decision."""
        explanation = DecisionExplanation(decision_id=decision_id)
        
        # Extract basic information
        query = decision_data.get("query", "")
        reasoning = decision_data.get("reasoning", "")
        confidence = decision_data.get("confidence", 0.0)
        options = decision_data.get("options", [])
        selected_option_id = decision_data.get("selected_option_id")
        
        # Generate summary
        explanation.summary = self._generate_summary(query, reasoning, options, selected_option_id)
        
        # Build reasoning chain from trace if available
        if trace:
            explanation.reasoning_chain = self._extract_reasoning_chain(trace)
        else:
            explanation.reasoning_chain = self._build_reasoning_chain(decision_data)
        
        # Extract key factors
        explanation.key_factors = self._extract_key_factors(decision_data)
        
        # Extract evidence
        explanation.evidence = self._extract_evidence(decision_data)
        
        # List alternatives
        explanation.alternatives_considered = self._list_alternatives(options, selected_option_id)
        
        # Assess risks
        explanation.risks_assessed = self._assess_risks(options, selected_option_id)
        
        # Extract assumptions
        explanation.assumptions = self._extract_assumptions(decision_data)
        
        # Set confidence
        explanation.confidence_level = confidence
        explanation.confidence_explanation = self._explain_confidence(confidence)
        
        logger.info(f"Generated explanation for decision {decision_id}")
        
        return explanation
    
    def _generate_summary(
        self,
        query: str,
        reasoning: str,
        options: List[Dict[str, Any]],
        selected_option_id: Optional[str],
    ) -> str:
        """Generate a summary of the decision."""
        selected_option = next(
            (opt for opt in options if opt.get("id") == selected_option_id),
            None,
        )
        
        if selected_option:
            action_desc = selected_option.get("description", "an action")
            return f"For the query '{query}', the system selected {action_desc}. {reasoning}"
        else:
            return f"For the query '{query}', the system made a decision based on {reasoning}"
    
    def _extract_reasoning_chain(self, trace: DecisionTrace) -> List[str]:
        """Extract reasoning chain from trace events."""
        chain = []
        
        for event in trace.events:
            if event.data:
                if "reasoning" in event.data:
                    chain.append(event.data["reasoning"])
                elif "explanation" in event.data:
                    chain.append(event.data["explanation"])
                elif "step" in event.data:
                    chain.append(event.data["step"])
        
        return chain
    
    def _build_reasoning_chain(self, decision_data: Dict[str, Any]) -> List[str]:
        """Build reasoning chain from decision data."""
        chain = []
        
        reasoning = decision_data.get("reasoning", "")
        if reasoning:
            chain.append(reasoning)
        
        context = decision_data.get("context", {})
        if context:
            chain.append(f"Decision made in context: {context.get('time_horizon', 'unknown')} time horizon")
        
        return chain
    
    def _extract_key_factors(self, decision_data: Dict[str, Any]) -> List[str]:
        """Extract key factors that influenced the decision."""
        factors = []
        
        context = decision_data.get("context", {})
        if context.get("objectives"):
            factors.extend([f"Objective: {obj}" for obj in context["objectives"]])
        
        if context.get("constraints"):
            factors.extend([f"Constraint: {c}" for c in context["constraints"]])
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            if selected.get("benefits"):
                factors.extend([f"Benefit: {b}" for b in selected["benefits"][:3]])
        
        return factors
    
    def _extract_evidence(self, decision_data: Dict[str, Any]) -> List[str]:
        """Extract evidence that supported the decision."""
        evidence = []
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            if selected.get("expected_outcome"):
                outcome = selected["expected_outcome"]
                if isinstance(outcome, dict):
                    for key, value in outcome.items():
                        evidence.append(f"Expected {key}: {value}")
        
        return evidence
    
    def _list_alternatives(
        self,
        options: List[Dict[str, Any]],
        selected_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """List alternatives that were considered."""
        alternatives = []
        
        for opt in options:
            if opt.get("id") != selected_id:
                alternatives.append({
                    "description": opt.get("description", "Unknown"),
                    "utility_score": opt.get("utility_score", 0.0),
                    "risk_score": opt.get("risk_score", 0.0),
                    "reason": "Not selected due to lower utility or higher risk",
                })
        
        return alternatives
    
    def _assess_risks(
        self,
        options: List[Dict[str, Any]],
        selected_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Assess risks that were evaluated."""
        risks = []
        
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            risk_score = selected.get("risk_score", 0.0)
            risks.append({
                "type": "Overall Risk",
                "level": "High" if risk_score > 0.7 else "Medium" if risk_score > 0.4 else "Low",
                "score": risk_score,
            })
            
            if selected.get("drawbacks"):
                for drawback in selected["drawbacks"]:
                    risks.append({
                        "type": "Drawback",
                        "level": "Medium",
                        "description": drawback,
                    })
        
        return risks
    
    def _extract_assumptions(self, decision_data: Dict[str, Any]) -> List[str]:
        """Extract assumptions made in the decision."""
        assumptions = []
        
        context = decision_data.get("context", {})
        assumptions.append(f"Risk tolerance: {context.get('risk_tolerance', 0.5)}")
        assumptions.append(f"Time horizon: {context.get('time_horizon', 'medium')}")
        
        options = decision_data.get("options", [])
        if options:
            assumptions.append(f"Generated {len(options)} alternative options")
        
        return assumptions
    
    def _explain_confidence(self, confidence: float) -> str:
        """Generate an explanation for the confidence level."""
        if confidence >= 0.8:
            return "High confidence based on strong evidence and low uncertainty"
        elif confidence >= 0.6:
            return "Moderate confidence with some uncertainty factors"
        elif confidence >= 0.4:
            return "Low confidence due to limited evidence or high uncertainty"
        else:
            return "Very low confidence - decision should be reviewed"
    
    def generate_simple_explanation(
        self,
        decision_data: Dict[str, Any],
    ) -> str:
        """Generate a simple one-paragraph explanation."""
        query = decision_data.get("query", "")
        reasoning = decision_data.get("reasoning", "")
        confidence = decision_data.get("confidence", 0.0)
        
        return f"For '{query}', the decision was: {reasoning} Confidence: {confidence:.1%}"
