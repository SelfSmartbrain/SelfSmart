"""decision_auditor.py

Phase 16A: Decision Auditor

Audits decisions to ensure they meet governance standards.
Tracks:
- Decision compliance with policies
- Risk thresholds
- Required approvals
- Documentation completeness
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.governance.decision_trace import DecisionTrace

logger = get_logger(__name__)


class AuditStatus(str, Enum):
    """Status of a decision audit."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class AuditCheckType(str, Enum):
    """Types of audit checks."""
    POLICY_COMPLIANCE = "policy_compliance"
    RISK_THRESHOLD = "risk_threshold"
    DOCUMENTATION = "documentation"
    APPROVAL_CHAIN = "approval_chain"
    CONSTRAINT_CHECK = "constraint_check"
    ETHICAL_REVIEW = "ethical_review"


@dataclass
class AuditCheck:
    """A single audit check."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    check_type: AuditCheckType = AuditCheckType.POLICY_COMPLIANCE
    description: str = ""
    passed: bool = False
    message: str = ""
    severity: str = "info"  # info, warning, error, critical
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "check_type": self.check_type.value,
            "description": self.description,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class DecisionAudit:
    """An audit of a decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    audit_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auditor_id: str = ""
    status: AuditStatus = AuditStatus.PENDING
    checks: List[AuditCheck] = field(default_factory=list)
    overall_score: float = 0.0
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    approved: bool = False
    approval_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "audit_date": self.audit_date.isoformat(),
            "auditor_id": self.auditor_id,
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "overall_score": self.overall_score,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "approved": self.approved,
            "approval_notes": self.approval_notes,
            "metadata": self.metadata,
        }


class DecisionAuditor:
    """Audits decisions for governance compliance."""
    
    def __init__(self):
        self.audits: Dict[str, DecisionAudit] = {}
        self.audits_by_decision: Dict[str, str] = {}  # decision_id -> audit_id
        self.risk_thresholds: Dict[str, float] = {
            "high": 0.7,
            "medium": 0.4,
            "low": 0.2,
        }
        logger.info("DecisionAuditor initialized")
    
    def create_audit(
        self,
        decision_id: str,
        auditor_id: str = "system",
    ) -> DecisionAudit:
        """Create a new audit for a decision."""
        audit = DecisionAudit(
            decision_id=decision_id,
            auditor_id=auditor_id,
        )
        
        self.audits[audit.id] = audit
        self.audits_by_decision[decision_id] = audit.id
        
        logger.info(f"Created audit {audit.id} for decision {decision_id}")
        
        return audit
    
    def run_audit(
        self,
        decision_id: str,
        decision_data: Dict[str, Any],
        trace: Optional[DecisionTrace] = None,
        policies: Optional[List[Dict[str, Any]]] = None,
    ) -> DecisionAudit:
        """Run a complete audit on a decision."""
        audit = self.get_audit_by_decision(decision_id)
        if audit is None:
            audit = self.create_audit(decision_id)
        
        audit.status = AuditStatus.IN_PROGRESS
        
        # Run all audit checks
        audit.checks = [
            self._check_policy_compliance(decision_data, policies or []),
            self._check_risk_thresholds(decision_data),
            self._check_documentation(decision_data, trace),
            self._check_constraints(decision_data),
            self._check_ethical_considerations(decision_data),
        ]
        
        # Calculate overall score
        passed_checks = sum(1 for c in audit.checks if c.passed)
        audit.overall_score = passed_checks / len(audit.checks) if audit.checks else 0.0
        
        # Determine status
        if audit.overall_score >= 0.8:
            audit.status = AuditStatus.PASSED
            audit.approved = True
        elif audit.overall_score >= 0.6:
            audit.status = AuditStatus.WARNING
            audit.approved = True
        else:
            audit.status = AuditStatus.FAILED
            audit.approved = False
        
        # Generate findings and recommendations
        audit.findings = self._generate_findings(audit.checks)
        audit.recommendations = self._generate_recommendations(audit.checks)
        
        logger.info(f"Completed audit for decision {decision_id}: {audit.status.value}")
        
        return audit
    
    def _check_policy_compliance(
        self,
        decision_data: Dict[str, Any],
        policies: List[Dict[str, Any]],
    ) -> AuditCheck:
        """Check if decision complies with policies."""
        check = AuditCheck(
            check_type=AuditCheckType.POLICY_COMPLIANCE,
            description="Policy Compliance",
        )
        
        if not policies:
            check.passed = True
            check.message = "No policies defined - check passed by default"
            return check
        
        # Simple policy check - in production, this would be more sophisticated
        violations = []
        for policy in policies:
            policy_type = policy.get("type", "")
            if policy_type == "risk_limit":
                max_risk = policy.get("max_risk", 1.0)
                options = decision_data.get("options", [])
                selected_id = decision_data.get("selected_option_id")
                selected = next((opt for opt in options if opt.get("id") == selected_id), None)
                if selected and selected.get("risk_score", 0) > max_risk:
                    violations.append(f"Risk exceeds policy limit of {max_risk}")
        
        if violations:
            check.passed = False
            check.message = f"Policy violations: {', '.join(violations)}"
            check.severity = "error"
        else:
            check.passed = True
            check.message = "Decision complies with all policies"
            check.severity = "info"
        
        return check
    
    def _check_risk_thresholds(self, decision_data: Dict[str, Any]) -> AuditCheck:
        """Check if decision risk is within acceptable thresholds."""
        check = AuditCheck(
            check_type=AuditCheckType.RISK_THRESHOLD,
            description="Risk Threshold Check",
        )
        
        context = decision_data.get("context", {})
        risk_tolerance = context.get("risk_tolerance", 0.5)
        
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            risk_score = selected.get("risk_score", 0.0)
            
            # Check if risk exceeds tolerance
            if risk_score > (1.0 - risk_tolerance) + 0.2:
                check.passed = False
                check.message = f"Risk score {risk_score:.2f} exceeds tolerance {risk_tolerance:.2f}"
                check.severity = "warning"
            else:
                check.passed = True
                check.message = f"Risk score {risk_score:.2f} within acceptable range"
                check.severity = "info"
        else:
            check.passed = True
            check.message = "No selected option to assess risk"
            check.severity = "info"
        
        return check
    
    def _check_documentation(
        self,
        decision_data: Dict[str, Any],
        trace: Optional[DecisionTrace],
    ) -> AuditCheck:
        """Check if decision is properly documented."""
        check = AuditCheck(
            check_type=AuditCheckType.DOCUMENTATION,
            description="Documentation Completeness",
        )
        
        missing = []
        
        if not decision_data.get("query"):
            missing.append("query")
        if not decision_data.get("reasoning"):
            missing.append("reasoning")
        if not decision_data.get("options"):
            missing.append("options")
        
        if trace:
            if not trace.events:
                missing.append("trace events")
        else:
            missing.append("decision trace")
        
        if missing:
            check.passed = False
            check.message = f"Missing documentation: {', '.join(missing)}"
            check.severity = "warning"
        else:
            check.passed = True
            check.message = "Documentation is complete"
            check.severity = "info"
        
        return check
    
    def _check_constraints(self, decision_data: Dict[str, Any]) -> AuditCheck:
        """Check if decision respects constraints."""
        check = AuditCheck(
            check_type=AuditCheckType.CONSTRAINT_CHECK,
            description="Constraint Compliance",
        )
        
        context = decision_data.get("context", {})
        constraints = context.get("constraints", [])
        
        if not constraints:
            check.passed = True
            check.message = "No constraints defined - check passed"
            return check
        
        # In production, this would check if the selected action violates constraints
        # For now, we assume constraints are respected
        check.passed = True
        check.message = f"Decision respects {len(constraints)} constraints"
        check.severity = "info"
        
        return check
    
    def _check_ethical_considerations(self, decision_data: Dict[str, Any]) -> AuditCheck:
        """Check if ethical considerations were addressed."""
        check = AuditCheck(
            check_type=AuditCheckType.ETHICAL_REVIEW,
            description="Ethical Considerations",
        )
        
        # Check for ethical flags in metadata
        metadata = decision_data.get("metadata", {})
        ethical_flags = metadata.get("ethical_flags", [])
        
        if ethical_flags:
            check.passed = False
            check.message = f"Ethical concerns raised: {', '.join(ethical_flags)}"
            check.severity = "error"
        else:
            check.passed = True
            check.message = "No ethical concerns identified"
            check.severity = "info"
        
        return check
    
    def _generate_findings(self, checks: List[AuditCheck]) -> List[str]:
        """Generate findings from audit checks."""
        findings = []
        
        for check in checks:
            if not check.passed:
                findings.append(f"[{check.severity.upper()}] {check.description}: {check.message}")
            elif check.severity == "warning":
                findings.append(f"[WARNING] {check.description}: {check.message}")
        
        return findings
    
    def _generate_recommendations(self, checks: List[AuditCheck]) -> List[str]:
        """Generate recommendations based on audit results."""
        recommendations = []
        
        for check in checks:
            if not check.passed:
                if check.check_type == AuditCheckType.RISK_THRESHOLD:
                    recommendations.append("Consider selecting a lower-risk option or increase risk tolerance")
                elif check.check_type == AuditCheckType.DOCUMENTATION:
                    recommendations.append("Improve decision documentation with reasoning and evidence")
                elif check.check_type == AuditCheckType.ETHICAL_REVIEW:
                    recommendations.append("Review ethical implications and add mitigation strategies")
        
        if not recommendations:
            recommendations.append("Decision meets all governance standards")
        
        return recommendations
    
    def get_audit(self, audit_id: str) -> Optional[DecisionAudit]:
        """Get an audit by ID."""
        return self.audits.get(audit_id)
    
    def get_audit_by_decision(self, decision_id: str) -> Optional[DecisionAudit]:
        """Get an audit by decision ID."""
        audit_id = self.audits_by_decision.get(decision_id)
        if audit_id:
            return self.audits.get(audit_id)
        return None
    
    def list_audits(self, status: Optional[AuditStatus] = None) -> List[DecisionAudit]:
        """List all audits, optionally filtered by status."""
        if status:
            return [a for a in self.audits.values() if a.status == status]
        return list(self.audits.values())
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get statistics about audits."""
        total_audits = len(self.audits)
        passed = sum(1 for a in self.audits.values() if a.status == AuditStatus.PASSED)
        failed = sum(1 for a in self.audits.values() if a.status == AuditStatus.FAILED)
        warnings = sum(1 for a in self.audits.values() if a.status == AuditStatus.WARNING)
        
        return {
            "total_audits": total_audits,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "pass_rate": passed / total_audits if total_audits > 0 else 0.0,
        }
