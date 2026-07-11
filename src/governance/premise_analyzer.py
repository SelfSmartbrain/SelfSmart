"""premise_analyzer.py

Phase 16B: Premise Analyzer

Analyzes premises and foundational assumptions in strategies.
Identifies:
- Untested premises
- Premises with weak evidence
- Contradictory premises
- Premises that need validation
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class PremiseStatus(str, Enum):
    """Status of a premise."""
    UNTESTED = "untested"
    VALIDATED = "validated"
    REFUTED = "refuted"
    WEAK = "weak"
    CONTRADICTED = "contradicted"


class PremiseCategory(str, Enum):
    """Categories of premises."""
    FACTUAL = "factual"
    CAUSAL = "causal"
    NORMATIVE = "normative"
    PREDICTIVE = "predictive"
    STRATEGIC = "strategic"


@dataclass
class Premise:
    """A premise underlying a decision or strategy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    category: PremiseCategory = PremiseCategory.FACTUAL
    status: PremiseStatus = PremiseStatus.UNTESTED
    confidence: float = 0.5
    evidence_strength: float = 0.0
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # IDs of dependent premises
    test_method: Optional[str] = None
    last_tested: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "category": self.category.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "evidence_strength": self.evidence_strength,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "dependencies": self.dependencies,
            "test_method": self.test_method,
            "last_tested": self.last_tested,
            "metadata": self.metadata,
        }


class PremiseAnalyzer:
    """Analyzes premises in strategies and decisions."""
    
    def __init__(self):
        self.premises: Dict[str, Premise] = {}
        logger.info("PremiseAnalyzer initialized")
    
    def extract_premises(
        self,
        strategy_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Premise]:
        """Extract premises from strategy text."""
        premises = []
        context = context or {}
        
        # Look for premise indicators
        premise_indicators = [
            "based on",
            "assuming",
            "given that",
            "since",
            "because",
            "premise",
            "foundation",
            "underlying",
        ]
        
        sentences = strategy_text.split(".")
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains a premise indicator
            if any(indicator in sentence.lower() for indicator in premise_indicators):
                premise = Premise(
                    statement=sentence,
                    category=self._classify_premise(sentence),
                    status=PremiseStatus.UNTESTED,
                    confidence=0.5,
                )
                premises.append(premise)
        
        # Extract premises from context
        premises.extend(self._extract_from_context(context))
        
        # Store premises
        for premise in premises:
            self.premises[premise.id] = premise
        
        logger.info(f"Extracted {len(premises)} premises")
        
        return premises
    
    def _classify_premise(self, statement: str) -> PremiseCategory:
        """Classify a premise by category."""
        statement_lower = statement.lower()
        
        if any(word in statement_lower for word in ["will", "predict", "expect", "forecast"]):
            return PremiseCategory.PREDICTIVE
        elif any(word in statement_lower for word in ["should", "must", "ought", "right"]):
            return PremiseCategory.NORMATIVE
        elif any(word in statement_lower for word in ["cause", "because", "due to", "leads to"]):
            return PremiseCategory.CAUSAL
        elif any(word in statement_lower for word in ["strategy", "plan", "approach", "method"]):
            return PremiseCategory.STRATEGIC
        else:
            return PremiseCategory.FACTUAL
    
    def _extract_from_context(self, context: Dict[str, Any]) -> List[Premise]:
        """Extract premises from decision context."""
        premises = []
        
        # From constraints
        constraints = context.get("constraints", [])
        for constraint in constraints:
            premises.append(Premise(
                statement=f"Constraint: {constraint}",
                category=PremiseCategory.STRATEGIC,
                status=PremiseStatus.UNTESTED,
                confidence=0.6,
            ))
        
        # From objectives
        objectives = context.get("objectives", [])
        for objective in objectives:
            premises.append(Premise(
                statement=f"Objective: {objective}",
                category=PremiseCategory.NORMATIVE,
                status=PremiseStatus.UNTESTED,
                confidence=0.5,
            ))
        
        return premises
    
    def analyze_premise(self, premise: Premise) -> Dict[str, Any]:
        """Analyze a premise for strength and validity."""
        analysis = {
            "premise_id": premise.id,
            "strength": self._calculate_premise_strength(premise),
            "validation_needed": premise.status == PremiseStatus.UNTESTED,
            "contradiction_risk": len(premise.contradicting_evidence) > 0,
            "evidence_quality": self._assess_evidence_quality(premise),
            "recommendations": self._generate_premise_recommendations(premise),
        }
        
        return analysis
    
    def _calculate_premise_strength(self, premise: Premise) -> float:
        """Calculate the strength of a premise."""
        factors = []
        
        # Evidence strength
        factors.append(premise.evidence_strength)
        
        # Confidence
        factors.append(premise.confidence)
        
        # Supporting vs contradicting evidence ratio
        total_evidence = len(premise.supporting_evidence) + len(premise.contradicting_evidence)
        if total_evidence > 0:
            support_ratio = len(premise.supporting_evidence) / total_evidence
            factors.append(support_ratio)
        else:
            factors.append(0.5)
        
        # Status bonus
        if premise.status == PremiseStatus.VALIDATED:
            factors.append(1.0)
        elif premise.status == PremiseStatus.REFUTED:
            factors.append(0.0)
        else:
            factors.append(0.5)
        
        return sum(factors) / len(factors)
    
    def _assess_evidence_quality(self, premise: Premise) -> str:
        """Assess the quality of evidence for a premise."""
        if premise.status == PremiseStatus.VALIDATED:
            return "high"
        elif premise.status == PremiseStatus.REFUTED:
            return "invalid"
        elif premise.evidence_strength > 0.7:
            return "high"
        elif premise.evidence_strength > 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_premise_recommendations(self, premise: Premise) -> List[str]:
        """Generate recommendations for a premise."""
        recommendations = []
        
        if premise.status == PremiseStatus.UNTESTED:
            recommendations.append("This premise needs validation")
            if premise.test_method:
                recommendations.append(f"Suggested test: {premise.test_method}")
            else:
                recommendations.append("Define a test method to validate this premise")
        
        if premise.evidence_strength < 0.5:
            recommendations.append("Gather more supporting evidence")
        
        if premise.contradicting_evidence:
            recommendations.append("Address contradicting evidence")
        
        if premise.confidence < 0.5:
            recommendations.append("Increase confidence through validation")
        
        if not recommendations:
            recommendations.append("Premise appears sound")
        
        return recommendations
    
    def detect_contradictions(self) -> List[Dict[str, Any]]:
        """Detect contradictions between premises."""
        contradictions = []
        
        premise_list = list(self.premises.values())
        
        for i, premise1 in enumerate(premise_list):
            for premise2 in premise_list[i+1:]:
                if self._premises_contradict(premise1, premise2):
                    contradictions.append({
                        "premise1_id": premise1.id,
                        "premise1_statement": premise1.statement,
                        "premise2_id": premise2.id,
                        "premise2_statement": premise2.statement,
                        "severity": "high",
                    })
        
        return contradictions
    
    def _premises_contradict(self, premise1: Premise, premise2: Premise) -> bool:
        """Check if two premises contradict each other."""
        # Simple contradiction detection - in production, use semantic analysis
        words1 = set(premise1.statement.lower().split())
        words2 = set(premise2.statement.lower().split())
        
        # Look for antonyms
        antonym_pairs = [
            ("will", "will not"),
            ("can", "cannot"),
            ("increase", "decrease"),
            ("success", "failure"),
            ("true", "false"),
        ]
        
        for word1, word2 in antonym_pairs:
            if word1 in words1 and word2 in words2:
                return True
            if word2 in words1 and word1 in words2:
                return True
        
        return False
    
    def validate_premise(
        self,
        premise_id: str,
        result: bool,
        evidence: Optional[str] = None,
    ) -> Premise:
        """Validate a premise with test results."""
        premise = self.premises.get(premise_id)
        if premise is None:
            raise ValueError(f"Premise {premise_id} not found")
        
        if result:
            premise.status = PremiseStatus.VALIDATED
            premise.supporting_evidence.append(evidence or "Validation successful")
            premise.confidence = min(1.0, premise.confidence + 0.2)
        else:
            premise.status = PremiseStatus.REFUTED
            premise.contradicting_evidence.append(evidence or "Validation failed")
            premise.confidence = max(0.0, premise.confidence - 0.3)
        
        premise.last_tested = evidence or "validation"
        
        logger.info(f"Validated premise {premise_id}: {result}")
        
        return premise
    
    def get_premise(self, premise_id: str) -> Optional[Premise]:
        """Get a premise by ID."""
        return self.premises.get(premise_id)
    
    def get_premises_by_status(self, status: PremiseStatus) -> List[Premise]:
        """Get all premises with a specific status."""
        return [p for p in self.premises.values() if p.status == status]
    
    def get_premises_by_category(self, category: PremiseCategory) -> List[Premise]:
        """Get all premises of a specific category."""
        return [p for p in self.premises.values() if p.category == category]
    
    def get_premise_statistics(self) -> Dict[str, Any]:
        """Get statistics about premises."""
        total_premises = len(self.premises)
        
        by_status = {
            status.value: len(self.get_premises_by_status(status))
            for status in PremiseStatus
        }
        
        by_category = {
            category.value: len(self.get_premises_by_category(category))
            for category in PremiseCategory
        }
        
        contradictions = self.detect_contradictions()
        
        return {
            "total_premises": total_premises,
            "by_status": by_status,
            "by_category": by_category,
            "contradictions_detected": len(contradictions),
            "untested_premises": len(self.get_premises_by_status(PremiseStatus.UNTESTED)),
        }
