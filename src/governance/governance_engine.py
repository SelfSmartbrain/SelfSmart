"""governance_engine.py

Phase 16D: Governance Engine

Orchestrates governance components to ensure decisions meet standards.
Integrates:
- Policy enforcement
- Constraint checking
- Decision auditing
- Compliance tracking
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.governance.policy_manager import PolicyManager
from src.governance.constraint_system import ConstraintSystem
from src.governance.decision_auditor import DecisionAuditor

logger = get_logger(__name__)


@dataclass
class GovernanceResult:
    """Result of governance evaluation."""

    decision_id: str = ""
    approved: bool = False
    compliance_score: float = 0.0
    policy_compliance: Dict[str, Any] = field(default_factory=dict)
    constraint_compliance: Dict[str, Any] = field(default_factory=dict)
    audit_result: Optional[Dict[str, Any]] = None
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "approved": self.approved,
            "compliance_score": self.compliance_score,
            "policy_compliance": self.policy_compliance,
            "constraint_compliance": self.constraint_compliance,
            "audit_result": self.audit_result,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class GovernanceEngine:
    """Main governance engine for decision oversight."""

    def __init__(
        self,
        policy_manager: Optional[PolicyManager] = None,
        constraint_system: Optional[ConstraintSystem] = None,
        decision_auditor: Optional[DecisionAuditor] = None,
    ):
        self.policy_manager = policy_manager or PolicyManager()
        self.constraint_system = constraint_system or ConstraintSystem()
        self.decision_auditor = decision_auditor or DecisionAuditor()

        self.governance_history: Dict[str, GovernanceResult] = {}

        logger.info("GovernanceEngine initialized")

    def evaluate_decision(
        self,
        decision_data: Dict[str, Any],
        trace: Optional[Any] = None,
        require_audit: bool = True,
    ) -> GovernanceResult:
        """Evaluate a decision against all governance standards."""
        decision_id = decision_data.get("id", "")

        logger.info(f"Evaluating governance for decision: {decision_id}")

        result = GovernanceResult(decision_id=decision_id)

        # Check policy compliance
        policy_result = self.policy_manager.check_compliance(decision_data)
        result.policy_compliance = policy_result

        # Check constraint compliance
        constraint_result = self.constraint_system.check_constraints(decision_data)
        result.constraint_compliance = constraint_result

        # Run audit if required
        if require_audit:
            audit = self.decision_auditor.run_audit(decision_id, decision_data, trace)
            result.audit_result = audit.to_dict()

        # Calculate overall compliance score
        result.compliance_score = self._calculate_compliance_score(result)

        # Determine approval
        result.approved = self._determine_approval(result)

        # Generate findings and recommendations
        result.findings = self._generate_findings(result)
        result.recommendations = self._generate_recommendations(result)

        # Store result
        self.governance_history[decision_id] = result

        logger.info(f"Governance evaluation complete: {decision_id} - Approved: {result.approved}")

        return result

    async def evaluate_decision_async(
        self,
        decision_data: Dict[str, Any],
        trace: Optional[Any] = None,
        require_audit: bool = True,
    ) -> GovernanceResult:
        """Non-blocking async version of evaluate_decision."""
        import asyncio

        return await asyncio.to_thread(self.evaluate_decision, decision_data, trace, require_audit)

    def _calculate_compliance_score(self, result: GovernanceResult) -> float:
        """Calculate overall compliance score."""
        scores = []

        # Policy compliance score
        if result.policy_compliance.get("overall_compliant"):
            scores.append(1.0)
        else:
            # Partial credit based on policies passed
            total = result.policy_compliance.get("policies_checked", 0)
            if total > 0:
                passed = total - len(result.policy_compliance.get("results", []))
                scores.append(passed / total)

        # Constraint compliance score
        if not result.constraint_compliance.get("hard_violations"):
            scores.append(1.0)
        else:
            scores.append(0.5)

        # Audit score
        if result.audit_result:
            audit_score = result.audit_result.get("overall_score", 0.0)
            scores.append(audit_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _determine_approval(self, result: GovernanceResult) -> bool:
        """Determine if decision is approved."""
        # Must have no hard constraint violations
        if result.constraint_compliance.get("hard_violations"):
            return False

        # Must meet minimum compliance threshold
        if result.compliance_score < 0.6:
            return False

        # If audit exists, must pass
        if result.audit_result:
            audit_status = result.audit_result.get("status", "")
            if audit_status == "failed":
                return False

        return True

    def _generate_findings(self, result: GovernanceResult) -> List[str]:
        """Generate findings from governance evaluation."""
        findings = []

        # Policy findings
        if not result.policy_compliance.get("overall_compliant"):
            findings.append("Decision does not comply with all policies")

        # Constraint findings
        if result.constraint_compliance.get("hard_violations"):
            findings.append("Decision violates hard constraints")

        # Audit findings
        if result.audit_result:
            audit_findings = result.audit_result.get("findings", [])
            findings.extend(audit_findings)

        return findings

    def _generate_recommendations(self, result: GovernanceResult) -> List[str]:
        """Generate recommendations from governance evaluation."""
        recommendations = []

        # Policy recommendations
        for policy_result in result.policy_compliance.get("results", []):
            if not policy_result.get("compliant"):
                recommendations.append(
                    f"Address violations in policy: {policy_result.get('policy_name')}"
                )

        # Constraint recommendations
        violations = result.constraint_compliance.get("violations", [])
        for violation in violations:
            recommendations.append(f"Resolve constraint violation: {violation.get('description')}")

        # Audit recommendations
        if result.audit_result:
            audit_recommendations = result.audit_result.get("recommendations", [])
            recommendations.extend(audit_recommendations)

        return recommendations

    def get_governance_result(self, decision_id: str) -> Optional[GovernanceResult]:
        """Get governance result for a decision."""
        return self.governance_history.get(decision_id)

    def get_governance_statistics(self) -> Dict[str, Any]:
        """Get governance statistics."""
        total_evaluations = len(self.governance_history)
        approved = sum(1 for r in self.governance_history.values() if r.approved)

        avg_compliance = (
            sum(r.compliance_score for r in self.governance_history.values()) / total_evaluations
            if total_evaluations > 0
            else 0.0
        )

        return {
            "total_evaluations": total_evaluations,
            "approved": approved,
            "rejected": total_evaluations - approved,
            "approval_rate": approved / total_evaluations if total_evaluations > 0 else 0.0,
            "average_compliance_score": avg_compliance,
            "policy_stats": self.policy_manager.get_policy_statistics(),
            "constraint_stats": self.constraint_system.get_constraint_statistics(),
            "audit_stats": self.decision_auditor.get_audit_statistics(),
        }
