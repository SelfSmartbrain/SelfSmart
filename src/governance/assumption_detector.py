"""assumption_detector.py

Phase 16B: Assumption Detector

Identifies hidden assumptions in decision-making strategies.
Detects:
- Implicit beliefs about the environment
- Unstated dependencies
- Assumptions about resource availability
- Assumptions about time constraints
- Assumptions about stakeholder behavior
"""

from __future__ import annotations

import uuid
import re
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger

logger = get_logger(__name__)


class AssumptionType(str, Enum):
    """Types of assumptions."""
    RESOURCE = "resource"
    TIME = "time"
    DEPENDENCY = "dependency"
    STAKEHOLDER = "stakeholder"
    ENVIRONMENT = "environment"
    TECHNICAL = "technical"
    UNCERTAINTY = "uncertainty"


class AssumptionStrength(str, Enum):
    """Strength of an assumption."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    SPECULATIVE = "speculative"


@dataclass
class Assumption:
    """An identified assumption."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assumption_type: AssumptionType = AssumptionType.RESOURCE
    description: str = ""
    source: str = ""  # where this assumption was found
    strength: AssumptionStrength = AssumptionStrength.MODERATE
    confidence: float = 0.5
    testable: bool = True
    tested: bool = False
    test_result: Optional[bool] = None
    verification_method: Optional[str] = None  # "database", "context_fallback", "heuristic", etc.
    impact_if_wrong: str = "medium"
    mitigation_strategy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assumption_type": self.assumption_type.value,
            "description": self.description,
            "source": self.source,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "testable": self.testable,
            "tested": self.tested,
            "test_result": self.test_result,
            "verification_method": self.verification_method,
            "impact_if_wrong": self.impact_if_wrong,
            "mitigation_strategy": self.mitigation_strategy,
            "metadata": self.metadata,
        }


class AssumptionDetector:
    """Detects hidden assumptions in strategies and decisions."""

    _ROW_COUNT_PATTERN = re.compile(
        r"(?P<table>[A-Za-z_][A-Za-z0-9_]*)\s+has\s+"
        r"(?:(?P<lt>fewer|less)\s+than|"
        r"(?P<gt>more|greater)\s+than|"
        r"(?P<ge>at\s+least)|"
        r"(?P<le>at\s+most)|"
        r"(?P<eq>exactly))\s+"
        r"(?P<count>\d+)\s+rows?",
        re.IGNORECASE,
    )
    
    def __init__(self):
        self.assumption_patterns = {
            AssumptionType.RESOURCE: [
                r"we have (enough|sufficient) (resources|budget|compute)",
                r"resource (availability|constraints)",
                r"budget (limit|cap)",
            ],
            AssumptionType.TIME: [
                r"within (time|deadline)",
                r"(quick|fast) enough",
                r"time (constraint|limit)",
            ],
            AssumptionType.DEPENDENCY: [
                r"(depends|relies) on",
                r"requires (that|the)",
                r"assuming (that|the)",
            ],
            AssumptionType.STAKEHOLDER: [
                r"(user|customer|stakeholder) will",
                r"(market|demand) will",
                r"(accept|adopt|use)",
            ],
            AssumptionType.ENVIRONMENT: [
                r"(market|environment) conditions",
                r"(external|outside) factors",
                r"(stable|unchanged)",
            ],
            AssumptionType.TECHNICAL: [
                r"(technology|system) can",
                r"(feasible|possible) to",
                r"(technical|engineering) constraints",
            ],
            AssumptionType.UNCERTAINTY: [
                r"(likely|probably|expected)",
                r"(low|high) probability",
                r"(uncertainty|risk) is",
            ],
        }
        logger.info("AssumptionDetector initialized")
    
    def detect_assumptions(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Assumption]:
        """Detect assumptions in text."""
        assumptions = []
        context = context or {}
        
        for assumption_type, patterns in self.assumption_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    assumption = Assumption(
                        assumption_type=assumption_type,
                        description=match.group(0),
                        source="text_analysis",
                        strength=self._infer_strength(match.group(0)),
                        confidence=0.7,
                    )
                    assumptions.append(assumption)
        
        # Detect assumptions from context
        assumptions.extend(self._detect_from_context(context))
        
        logger.info(f"Detected {len(assumptions)} assumptions")
        
        return assumptions
    
    def _infer_strength(self, text: str) -> AssumptionStrength:
        """Infer the strength of an assumption from text."""
        strong_indicators = ["certain", "definitely", "will", "must"]
        weak_indicators = ["might", "could", "possibly", "maybe", "likely"]
        
        text_lower = text.lower()
        
        if any(indicator in text_lower for indicator in strong_indicators):
            return AssumptionStrength.STRONG
        elif any(indicator in text_lower for indicator in weak_indicators):
            return AssumptionStrength.WEAK
        else:
            return AssumptionStrength.MODERATE
    
    def _detect_from_context(self, context: Dict[str, Any]) -> List[Assumption]:
        """Detect assumptions from decision context."""
        assumptions = []
        
        # Resource assumptions
        resources = context.get("available_resources", {})
        if resources:
            for resource, value in resources.items():
                assumptions.append(Assumption(
                    assumption_type=AssumptionType.RESOURCE,
                    description=f"Resource {resource} will be available at level {value}",
                    source="context",
                    strength=AssumptionStrength.MODERATE,
                ))
        
        # Time assumptions
        time_horizon = context.get("time_horizon")
        if time_horizon:
            assumptions.append(Assumption(
                assumption_type=AssumptionType.TIME,
                description=f"Time horizon of {time_horizon} is appropriate",
                source="context",
                strength=AssumptionStrength.MODERATE,
            ))
        
        # Constraint assumptions
        constraints = context.get("constraints", [])
        for constraint in constraints:
            assumptions.append(Assumption(
                assumption_type=AssumptionType.DEPENDENCY,
                description=f"Constraint '{constraint}' will hold",
                source="context",
                strength=AssumptionStrength.MODERATE,
            ))
        
        return assumptions
    
    def detect_from_decision(self, decision_data: Dict[str, Any]) -> List[Assumption]:
        """Detect assumptions from a complete decision."""
        assumptions = []
        
        # From reasoning
        reasoning = decision_data.get("reasoning", "")
        if reasoning:
            assumptions.extend(self.detect_assumptions(reasoning))
        
        # From context
        context = decision_data.get("context", {})
        assumptions.extend(self._detect_from_context(context))
        
        # From selected option
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            # From benefits
            for benefit in selected.get("benefits", []):
                assumptions.extend(self.detect_assumptions(benefit))
            
            # From drawbacks
            for drawback in selected.get("drawbacks", []):
                assumptions.extend(self.detect_assumptions(drawback))
        
        # Remove duplicates
        unique_assumptions = self._deduplicate_assumptions(assumptions)
        
        return unique_assumptions
    
    def _deduplicate_assumptions(self, assumptions: List[Assumption]) -> List[Assumption]:
        """Remove duplicate assumptions."""
        seen = set()
        unique = []
        
        for assumption in assumptions:
            key = (assumption.assumption_type, assumption.description.lower())
            if key not in seen:
                seen.add(key)
                unique.append(assumption)
        
        return unique
    
    def assess_assumption_risk(self, assumption: Assumption) -> Dict[str, Any]:
        """Assess the risk if an assumption is wrong."""
        risk_factors = {
            "strength": {
                AssumptionStrength.STRONG: 0.8,
                AssumptionStrength.MODERATE: 0.5,
                AssumptionStrength.WEAK: 0.3,
                AssumptionStrength.SPECULATIVE: 0.2,
            },
            "impact": {
                "critical": 0.9,
                "high": 0.7,
                "medium": 0.5,
                "low": 0.3,
            },
        }
        
        strength_risk = risk_factors["strength"].get(assumption.strength, 0.5)
        impact_risk = risk_factors["impact"].get(assumption.impact_if_wrong, 0.5)
        
        overall_risk = strength_risk * impact_risk
        
        return {
            "assumption_id": assumption.id,
            "strength_risk": strength_risk,
            "impact_risk": impact_risk,
            "overall_risk": overall_risk,
            "risk_level": "high" if overall_risk > 0.6 else "medium" if overall_risk > 0.3 else "low",
        }
    
    def generate_mitigation(self, assumption: Assumption) -> str:
        """Generate a mitigation strategy for an assumption."""
        if not assumption.testable:
            return "Cannot test - consider reducing dependency on this assumption"
        
        if assumption.assumption_type == AssumptionType.RESOURCE:
            return "Implement resource monitoring and contingency planning"
        elif assumption.assumption_type == AssumptionType.TIME:
            return "Build in buffer time and milestone checkpoints"
        elif assumption.assumption_type == AssumptionType.DEPENDENCY:
            return "Identify alternative dependencies and reduce coupling"
        elif assumption.assumption_type == AssumptionType.STAKEHOLDER:
            return "Conduct stakeholder validation and gather feedback early"
        elif assumption.assumption_type == AssumptionType.ENVIRONMENT:
            return "Monitor environmental changes and have adaptation strategies"
        elif assumption.assumption_type == AssumptionType.TECHNICAL:
            return "Create proof-of-concept and technical validation"
        else:
            return "Monitor assumption validity and have contingency plans"
    
    async def test_assumption(
        self,
        assumption: Assumption,
        test_context: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Assumption:
        """Test an assumption and update its test_result field.
        
        This implementation performs real state verification for database row-count claims.
        For RESOURCE assumptions about database tables, it queries the actual database
        to verify the claim against ground truth.
        """
        test_context = test_context or {}
        
        if not assumption.testable:
            logger.warning(f"Assumption {assumption.id} is not testable")
            assumption.tested = True
            assumption.test_result = None
            assumption.verification_method = None
            return assumption
        
        test_passed = False
        
        if assumption.assumption_type == AssumptionType.RESOURCE:
            claim = self._parse_row_count_claim(assumption.description)
            if claim:
                table_name, comparison, claimed_count = claim
                actual_count = None

                if db_session:
                    row_count_query = select(func.count()).select_from(table(table_name))
                    try:
                        result = await db_session.execute(row_count_query)
                        actual_count = result.scalar()
                        assumption.verification_method = "database"
                    except Exception as exc:
                        assumption.metadata["verification_error"] = (
                            f"{type(exc).__name__}: {exc}"
                        )
                        logger.warning(
                            "Database verification failed for assumption %s: %s",
                            assumption.id,
                            exc,
                        )

                if actual_count is None:
                    actual_count = test_context.get("available_resources", {}).get(table_name)
                    assumption.verification_method = "context_fallback"

                if isinstance(actual_count, (int, float)) and not isinstance(actual_count, bool):
                    test_passed = self._compare_row_count(
                        actual_count,
                        comparison,
                        claimed_count,
                    )

                assumption.metadata["verification_details"] = {
                    "table": table_name,
                    "comparison": comparison,
                    "expected_count": claimed_count,
                    "actual_count": actual_count,
                }
                logger.info(
                    "Row-count check via %s: %s has %s rows, expected %s %s",
                    assumption.verification_method,
                    table_name,
                    actual_count,
                    comparison,
                    claimed_count,
                )
            else:
                available_resources = test_context.get("available_resources", {})
                test_passed = bool(available_resources)
                assumption.verification_method = "context_check"

        elif assumption.assumption_type == AssumptionType.TIME:
            # Check if time constraints are reasonable
            time_horizon = test_context.get("time_horizon")
            if time_horizon and time_horizon in ["short", "medium", "long"]:
                test_passed = True
            assumption.verification_method = "context_check"

        elif assumption.assumption_type == AssumptionType.DEPENDENCY:
            # Check if dependencies are available
            dependencies = test_context.get("dependencies", [])
            if dependencies:
                test_passed = True
            assumption.verification_method = "context_check"

        elif assumption.assumption_type == AssumptionType.TECHNICAL:
            # Check if technical feasibility can be validated
            technical_validation = test_context.get("technical_validation")
            if technical_validation is not None:
                test_passed = technical_validation
            assumption.verification_method = "context_check"

        else:
            # For other types, use a simple heuristic
            test_passed = assumption.confidence > 0.5
            assumption.verification_method = "heuristic"

        # Update assumption with test result
        assumption.tested = True
        assumption.test_result = test_passed

        logger.info(
            f"Tested assumption {assumption.id}: "
            f"{'PASSED' if test_passed else 'FAILED'}"
        )

        return assumption

    def _parse_row_count_claim(
        self,
        description: str,
    ) -> tuple[str, str, int] | None:
        """Parse a supported database row-count claim."""
        match = self._ROW_COUNT_PATTERN.search(description)
        if not match:
            return None

        if match.group("lt"):
            comparison = "less_than"
        elif match.group("gt"):
            comparison = "greater_than"
        elif match.group("ge"):
            comparison = "at_least"
        elif match.group("le"):
            comparison = "at_most"
        else:
            comparison = "exactly"

        return match.group("table"), comparison, int(match.group("count"))

    @staticmethod
    def _compare_row_count(
        actual_count: int | float,
        comparison: str,
        expected_count: int,
    ) -> bool:
        """Evaluate a parsed row-count comparison."""
        if comparison == "less_than":
            return actual_count < expected_count
        if comparison == "greater_than":
            return actual_count > expected_count
        if comparison == "at_least":
            return actual_count >= expected_count
        if comparison == "at_most":
            return actual_count <= expected_count
        return actual_count == expected_count
    
    async def test_assumptions_batch(
        self,
        assumptions: List[Assumption],
        test_context: Optional[Dict[str, Any]] = None,
    ) -> List[Assumption]:
        """Test multiple assumptions in batch."""
        test_context = test_context or {}
        
        tested_assumptions = []
        for assumption in assumptions:
            tested = await self.test_assumption(assumption, test_context)
            tested_assumptions.append(tested)
        
        logger.info(f"Tested {len(tested_assumptions)} assumptions in batch")
        
        return tested_assumptions
    
    async def invalidate_assumption(
        self,
        assumption: Assumption,
        reason: str,
    ) -> Assumption:
        """Mark an assumption as invalidated with a reason."""
        assumption.tested = True
        assumption.test_result = False
        assumption.metadata["invalidated"] = True
        assumption.metadata["invalidation_reason"] = reason
        assumption.metadata["invalidated_at"] = datetime.utcnow().isoformat()
        
        logger.warning(
            f"Invalidated assumption {assumption.id}: {reason}"
        )
        
        return assumption
    
    async def retest_invalidated_assumptions(
        self,
        assumptions: List[Assumption],
        test_context: Optional[Dict[str, Any]] = None,
    ) -> List[Assumption]:
        """Re-test assumptions that were previously invalidated."""
        test_context = test_context or {}
        
        invalidated = [
            a for a in assumptions
            if a.metadata.get("invalidated", False)
        ]
        
        if not invalidated:
            logger.info("No invalidated assumptions to re-test")
            return assumptions
        
        logger.info(f"Re-testing {len(invalidated)} invalidated assumptions")
        
        retested = []
        for assumption in invalidated:
            # Clear invalidation status
            assumption.metadata["invalidated"] = False
            assumption.metadata["invalidation_reason"] = None
            assumption.metadata["invalidated_at"] = None
            
            # Re-test
            retested_assumption = await self.test_assumption(assumption, test_context)
            retested.append(retested_assumption)
        
        return retested
    
    def get_assumption_test_summary(self, assumptions: List[Assumption]) -> Dict[str, Any]:
        """Get a summary of assumption testing results."""
        total = len(assumptions)
        tested = sum(1 for a in assumptions if a.tested)
        passed = sum(1 for a in assumptions if a.test_result is True)
        failed = sum(1 for a in assumptions if a.test_result is False)
        invalidated = sum(1 for a in assumptions if a.metadata.get("invalidated", False))
        
        return {
            "total_assumptions": total,
            "tested": tested,
            "untested": total - tested,
            "passed": passed,
            "failed": failed,
            "invalidated": invalidated,
            "test_rate": tested / total if total > 0 else 0.0,
            "pass_rate": passed / tested if tested > 0 else 0.0,
        }
