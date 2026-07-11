"""failure_pattern_detector.py

Phase 16C: Failure Pattern Detector

Identifies patterns that consistently lead to failed outcomes.
Focuses on:
- High-failure decision patterns
- Risk factors that correlate with failure
- Common failure modes
- Warning signs to avoid
"""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class FailureMode(str, Enum):
    """Types of failure modes."""
    RESOURCE_INSUFFICIENCY = "resource_insufficiency"
    TIMING_MISMATCH = "timing_mismatch"
    RISK_MISCALCULATION = "risk_miscalculation"
    CONSTRAINT_VIOLATION = "constraint_violation"
    ASSUMPTION_FAILURE = "assumption_failure"
    EXTERNAL_FACTOR = "external_factor"


@dataclass
class FailurePattern:
    """A pattern associated with failed outcomes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    failure_mode: FailureMode = FailureMode.RISK_MISCALCULATION
    failure_rate: float = 0.0
    sample_size: int = 0
    confidence: float = 0.0
    risk_factors: Dict[str, Any] = field(default_factory=dict)
    warning_signs: List[str] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "failure_mode": self.failure_mode.value,
            "failure_rate": self.failure_rate,
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "risk_factors": self.risk_factors,
            "warning_signs": self.warning_signs,
            "mitigation_strategies": self.mitigation_strategies,
            "examples": self.examples[:5],
            "metadata": self.metadata,
        }


class FailurePatternDetector:
    """Detects patterns that lead to failed outcomes."""
    
    def __init__(self):
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.decision_history: List[Dict[str, Any]] = []
        logger.info("FailurePatternDetector initialized")
    
    def add_decision(self, decision_data: Dict[str, Any]) -> None:
        """Add a decision to the history."""
        self.decision_history.append(decision_data)
        
        # Re-detect patterns periodically
        if len(self.decision_history) % 10 == 0:
            self.detect_patterns()
    
    def detect_patterns(self) -> List[FailurePattern]:
        """Detect failure patterns from decision history."""
        if len(self.decision_history) < 5:
            logger.info("Not enough decisions to detect failure patterns")
            return []
        
        # Separate failed from successful decisions
        failed = [
            d for d in self.decision_history
            if d.get("outcome") and not d.get("outcome", {}).get("success", False)
        ]
        
        successful = [
            d for d in self.decision_history
            if d.get("outcome", {}).get("success", False)
        ]
        
        if len(failed) < 3:
            logger.info("Not enough failed decisions to detect patterns")
            return []
        
        patterns = []
        
        # Detect resource insufficiency patterns
        patterns.extend(self._detect_resource_patterns(failed, successful))
        
        # Detect risk miscalculation patterns
        patterns.extend(self._detect_risk_patterns(failed, successful))
        
        # Detect timing patterns
        patterns.extend(self._detect_timing_patterns(failed, successful))
        
        # Detect constraint violation patterns
        patterns.extend(self._detect_constraint_patterns(failed, successful))
        
        # Store patterns
        for pattern in patterns:
            self.failure_patterns[pattern.id] = pattern
        
        logger.info(f"Detected {len(patterns)} failure patterns")
        
        return patterns
    
    def _detect_resource_patterns(
        self,
        failed: List[Dict[str, Any]],
        successful: List[Dict[str, Any]],
    ) -> List[FailurePattern]:
        """Detect resource-related failure patterns."""
        patterns = []
        
        # Analyze resource constraints in failed decisions
        fail_resources = []
        for decision in failed:
            resources = decision.get("context", {}).get("available_resources", {})
            if resources:
                fail_resources.append(resources)
        
        if len(fail_resources) >= 3:
            # Look for missing resource types
            from collections import Counter
            resource_types = []
            for resources in fail_resources:
                resource_types.extend(resources.keys())
            
            resource_counts = Counter(resource_types)
            
            # If resource diversity is low, might indicate insufficiency
            if len(resource_counts) <= 2:
                pattern = FailurePattern(
                    name="Limited Resource Diversity",
                    description="Decisions with limited resource types have higher failure rate",
                    failure_mode=FailureMode.RESOURCE_INSUFFICIENCY,
                    failure_rate=len(fail_resources) / (len(fail_resources) + len(successful)),
                    sample_size=len(fail_resources),
                    confidence=min(1.0, len(fail_resources) / 10),
                    risk_factors={"resource_diversity": len(resource_counts)},
                    warning_signs=[
                        "Few resource types available",
                        "Heavy reliance on single resource type",
                    ],
                    mitigation_strategies=[
                        "Diversify resource allocation",
                        "Ensure backup resources are available",
                    ],
                    examples=[d.get("id", "") for d in failed[:3]],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_risk_patterns(
        self,
        failed: List[Dict[str, Any]],
        successful: List[Dict[str, Any]],
    ) -> List[FailurePattern]:
        """Detect risk-related failure patterns."""
        patterns = []
        
        # Analyze risk scores in failed decisions
        fail_risks = []
        for decision in failed:
            options = decision.get("options", [])
            selected_id = decision.get("selected_option_id")
            selected = next((opt for opt in options if opt.get("id") == selected_id), None)
            if selected:
                risk = selected.get("risk_score", 0)
                fail_risks.append(risk)
        
        # Analyze risk scores in successful decisions
        success_risks = []
        for decision in successful:
            options = decision.get("options", [])
            selected_id = decision.get("selected_option_id")
            selected = next((opt for opt in options if opt.get("id") == selected_id), None)
            if selected:
                risk = selected.get("risk_score", 0)
                success_risks.append(risk)
        
        if len(fail_risks) >= 3:
            avg_fail_risk = sum(fail_risks) / len(fail_risks)
            avg_success_risk = sum(success_risks) / len(success_risks) if success_risks else 0
            
            # If failed decisions have significantly higher risk
            if avg_fail_risk > avg_success_risk + 0.2:
                pattern = FailurePattern(
                    name="High Risk Selection",
                    description="Selecting high-risk options correlates with failure",
                    failure_mode=FailureMode.RISK_MISCALCULATION,
                    failure_rate=len(fail_risks) / (len(fail_risks) + len(success_risks)),
                    sample_size=len(fail_risks),
                    confidence=min(1.0, len(fail_risks) / 10),
                    risk_factors={
                        "avg_fail_risk": avg_fail_risk,
                        "avg_success_risk": avg_success_risk,
                    },
                    warning_signs=[
                        f"Risk score > {avg_success_risk + 0.2:.2f}",
                        "High uncertainty in outcome prediction",
                    ],
                    mitigation_strategies=[
                        "Consider lower-risk alternatives",
                        "Implement risk mitigation strategies",
                        "Increase confidence through additional analysis",
                    ],
                    examples=[d.get("id", "") for d in failed[:3]],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_timing_patterns(
        self,
        failed: List[Dict[str, Any]],
        successful: List[Dict[str, Any]],
    ) -> List[FailurePattern]:
        """Detect timing-related failure patterns."""
        patterns = []
        
        # Analyze decision timing
        from datetime import datetime
        
        fail_hours = []
        for decision in failed:
            created_at = decision.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        fail_hours.append(dt.hour)
                    except:
                        continue
                else:
                    fail_hours.append(created_at.hour)
        
        if len(fail_hours) >= 3:
            from collections import Counter
            hour_counts = Counter(fail_hours)
            
            for hour, count in hour_counts.most_common(3):
                if count >= 3:
                    pattern = FailurePattern(
                        name=f"Timing Risk: Hour {hour}",
                        description=f"Decisions made around hour {hour} show higher failure rate",
                        failure_mode=FailureMode.TIMING_MISMATCH,
                        failure_rate=count / len(fail_hours),
                        sample_size=count,
                        confidence=min(1.0, count / 10),
                        risk_factors={"hour": hour},
                        warning_signs=[
                            f"Decision made around hour {hour}",
                        ],
                        mitigation_strategies=[
                            f"Avoid critical decisions around hour {hour}",
                            "Add additional review for decisions at this time",
                        ],
                        examples=[d.get("id", "") for d in failed[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_constraint_patterns(
        self,
        failed: List[Dict[str, Any]],
        successful: List[Dict[str, Any]],
    ) -> List[FailurePattern]:
        """Detect constraint-related failure patterns."""
        patterns = []
        
        # Analyze constraint violations
        fail_constraints = []
        for decision in failed:
            constraints = decision.get("context", {}).get("constraints", [])
            if constraints:
                fail_constraints.append(len(constraints))
        
        success_constraints = []
        for decision in successful:
            constraints = decision.get("context", {}).get("constraints", [])
            if constraints:
                success_constraints.append(len(constraints))
        
        if len(fail_constraints) >= 3:
            avg_fail_constraints = sum(fail_constraints) / len(fail_constraints)
            avg_success_constraints = sum(success_constraints) / len(success_constraints) if success_constraints else 0
            
            # If failed decisions have significantly more constraints
            if avg_fail_constraints > avg_success_constraints + 1:
                pattern = FailurePattern(
                    name="Excessive Constraints",
                    description="Decisions with many constraints have higher failure rate",
                    failure_mode=FailureMode.CONSTRAINT_VIOLATION,
                    failure_rate=len(fail_constraints) / (len(fail_constraints) + len(success_constraints)),
                    sample_size=len(fail_constraints),
                    confidence=min(1.0, len(fail_constraints) / 10),
                    risk_factors={
                        "avg_fail_constraints": avg_fail_constraints,
                        "avg_success_constraints": avg_success_constraints,
                    },
                    warning_signs=[
                        f"More than {avg_success_constraints + 1:.0f} constraints",
                        "Complex constraint interactions",
                    ],
                    mitigation_strategies=[
                        "Simplify constraints where possible",
                        "Prioritize critical constraints",
                        "Validate constraint feasibility early",
                    ],
                    examples=[d.get("id", "") for d in failed[:3]],
                )
                patterns.append(pattern)
        
        return patterns
    
    def get_pattern(self, pattern_id: str) -> Optional[FailurePattern]:
        """Get a failure pattern by ID."""
        return self.failure_patterns.get(pattern_id)
    
    def get_patterns_by_mode(self, failure_mode: FailureMode) -> List[FailurePattern]:
        """Get all patterns of a specific failure mode."""
        return [p for p in self.failure_patterns.values() if p.failure_mode == failure_mode]
    
    def get_high_confidence_patterns(self, threshold: float = 0.7) -> List[FailurePattern]:
        """Get patterns with confidence above a threshold."""
        return [p for p in self.failure_patterns.values() if p.confidence >= threshold]
    
    def assess_decision_risk(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess a decision against known failure patterns."""
        risk_assessment = {
            "decision_id": decision_data.get("id", ""),
            "risk_level": "low",
            "matched_patterns": [],
            "warnings": [],
            "recommendations": [],
        }
        
        for pattern in self.failure_patterns.values():
            if pattern.confidence >= 0.6:
                match = self._check_pattern_match(decision_data, pattern)
                if match:
                    risk_assessment["matched_patterns"].append(pattern.id)
                    risk_assessment["warnings"].extend(pattern.warning_signs)
                    risk_assessment["recommendations"].extend(pattern.mitigation_strategies)
        
        # Determine overall risk level
        if len(risk_assessment["matched_patterns"]) >= 2:
            risk_assessment["risk_level"] = "high"
        elif len(risk_assessment["matched_patterns"]) >= 1:
            risk_assessment["risk_level"] = "medium"
        
        return risk_assessment
    
    def _check_pattern_match(self, decision_data: Dict[str, Any], pattern: FailurePattern) -> bool:
        """Check if a decision matches a failure pattern."""
        # Simple matching - in production, use more sophisticated analysis
        context = decision_data.get("context", {})
        
        if pattern.failure_mode == FailureMode.RESOURCE_INSUFFICIENCY:
            resources = context.get("available_resources", {})
            return len(resources) <= pattern.risk_factors.get("resource_diversity", 2)
        
        elif pattern.failure_mode == FailureMode.RISK_MISCALCULATION:
            options = decision_data.get("options", [])
            selected_id = decision_data.get("selected_option_id")
            selected = next((opt for opt in options if opt.get("id") == selected_id), None)
            if selected:
                risk = selected.get("risk_score", 0)
                threshold = pattern.risk_factors.get("avg_success_risk", 0.5) + 0.2
                return risk > threshold
        
        elif pattern.failure_mode == FailureMode.CONSTRAINT_VIOLATION:
            constraints = context.get("constraints", [])
            threshold = pattern.risk_factors.get("avg_success_constraints", 0) + 1
            return len(constraints) > threshold
        
        return False
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about failure patterns."""
        total_patterns = len(self.failure_patterns)
        
        by_mode = {
            failure_mode.value: len(self.get_patterns_by_mode(failure_mode))
            for failure_mode in FailureMode
        }
        
        avg_failure_rate = (
            sum(p.failure_rate for p in self.failure_patterns.values()) / total_patterns
            if total_patterns > 0 else 0.0
        )
        
        return {
            "total_patterns": total_patterns,
            "by_mode": by_mode,
            "average_failure_rate": avg_failure_rate,
            "decisions_analyzed": len(self.decision_history),
        }
