"""policy_manager.py

Phase 16D: Policy Manager

Manages governance policies that guide decision-making.
Supports:
- Policy creation and modification
- Policy enforcement
- Policy compliance tracking
- Policy versioning
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class PolicyType(str, Enum):
    """Types of policies."""
    RISK = "risk"
    ETHICAL = "ethical"
    RESOURCE = "resource"
    SAFETY = "safety"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"


class PolicyStatus(str, Enum):
    """Status of a policy."""
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass
class Policy:
    """A governance policy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    policy_type: PolicyType = PolicyType.STRATEGIC
    status: PolicyStatus = PolicyStatus.DRAFT
    rules: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    scope: List[str] = field(default_factory=list)  # what this policy applies to
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    compliance_count: int = 0
    violation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type.value,
            "status": self.status.value,
            "rules": self.rules,
            "parameters": self.parameters,
            "scope": self.scope,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "compliance_count": self.compliance_count,
            "violation_count": self.violation_count,
            "metadata": self.metadata,
        }


@dataclass
class PolicyCompliance:
    """A record of policy compliance check."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    decision_id: str = ""
    compliant: bool = False
    violations: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "decision_id": self.decision_id,
            "compliant": self.compliant,
            "violations": self.violations,
            "checked_at": self.checked_at.isoformat(),
            "metadata": self.metadata,
        }


class PolicyManager:
    """Manages governance policies."""
    
    def __init__(self):
        self.policies: Dict[str, Policy] = {}
        self.compliance_records: Dict[str, PolicyCompliance] = {}
        logger.info("PolicyManager initialized")
    
    def create_policy(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        rules: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        scope: Optional[List[str]] = None,
    ) -> Policy:
        """Create a new policy."""
        policy = Policy(
            name=name,
            description=description,
            policy_type=policy_type,
            rules=rules or [],
            parameters=parameters or {},
            scope=scope or [],
        )
        
        self.policies[policy.id] = policy
        logger.info(f"Created policy: {name}")
        
        return policy
    
    def update_policy(
        self,
        policy_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Policy]:
        """Update a policy."""
        policy = self.policies.get(policy_id)
        if policy is None:
            return None
        
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        policy.version += 1
        policy.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated policy: {policy_id} to version {policy.version}")
        
        return policy
    
    def activate_policy(self, policy_id: str) -> bool:
        """Activate a policy."""
        policy = self.policies.get(policy_id)
        if policy:
            policy.status = PolicyStatus.ACTIVE
            policy.effective_date = datetime.now(timezone.utc)
            logger.info(f"Activated policy: {policy_id}")
            return True
        return False
    
    def suspend_policy(self, policy_id: str) -> bool:
        """Suspend a policy."""
        policy = self.policies.get(policy_id)
        if policy:
            policy.status = PolicyStatus.SUSPENDED
            logger.info(f"Suspended policy: {policy_id}")
            return True
        return False
    
    def retire_policy(self, policy_id: str) -> bool:
        """Retire a policy."""
        policy = self.policies.get(policy_id)
        if policy:
            policy.status = PolicyStatus.RETIRED
            policy.expiry_date = datetime.now(timezone.utc)
            logger.info(f"Retired policy: {policy_id}")
            return True
        return False
    
    def check_compliance(
        self,
        decision_data: Dict[str, Any],
        policy_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check if a decision complies with policies."""
        active_policies = [
            p for p in self.policies.values()
            if p.status == PolicyStatus.ACTIVE
        ]
        
        if policy_id:
            active_policies = [p for p in active_policies if p.id == policy_id]
        
        compliance_results = []
        
        for policy in active_policies:
            result = self._check_policy_compliance(policy, decision_data)
            compliance_results.append(result)
            
            # Record compliance
            compliance_record = PolicyCompliance(
                policy_id=policy.id,
                decision_id=decision_data.get("id", ""),
                compliant=result["compliant"],
                violations=result["violations"],
            )
            self.compliance_records[compliance_record.id] = compliance_record
            
            # Update policy stats
            if result["compliant"]:
                policy.compliance_count += 1
            else:
                policy.violation_count += 1
        
        # Determine overall compliance
        all_compliant = all(r["compliant"] for r in compliance_results)
        
        return {
            "decision_id": decision_data.get("id", ""),
            "overall_compliant": all_compliant,
            "policies_checked": len(compliance_results),
            "results": compliance_results,
        }
    
    def _check_policy_compliance(
        self,
        policy: Policy,
        decision_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check compliance with a specific policy."""
        violations = []
        
        # Check each rule
        for rule in policy.rules:
            rule_type = rule.get("type")
            rule_params = rule.get("parameters", {})
            
            if rule_type == "risk_limit":
                max_risk = rule_params.get("max_risk", 1.0)
                options = decision_data.get("options", [])
                selected_id = decision_data.get("selected_option_id")
                selected = next((opt for opt in options if opt.get("id") == selected_id), None)
                
                if selected and selected.get("risk_score", 0) > max_risk:
                    violations.append(f"Risk exceeds limit: {selected.get('risk_score', 0)} > {max_risk}")
            
            elif rule_type == "resource_requirement":
                resource_type = rule_params.get("resource_type")
                min_amount = rule_params.get("min_amount", 0)
                context = decision_data.get("context", {})
                available = context.get("available_resources", {}).get(resource_type, 0)
                
                if available < min_amount:
                    violations.append(f"Insufficient {resource_type}: {available} < {min_amount}")
            
            elif rule_type == "ethical_check":
                ethical_flags = decision_data.get("metadata", {}).get("ethical_flags", [])
                forbidden = rule_params.get("forbidden", [])
                
                for flag in ethical_flags:
                    if any(f in flag.lower() for f in forbidden):
                        violations.append(f"Ethical violation: {flag}")
        
        return {
            "policy_id": policy.id,
            "policy_name": policy.name,
            "compliant": len(violations) == 0,
            "violations": violations,
        }
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self.policies.get(policy_id)
    
    def get_policies_by_type(self, policy_type: PolicyType) -> List[Policy]:
        """Get all policies of a specific type."""
        return [p for p in self.policies.values() if p.policy_type == policy_type]
    
    def get_active_policies(self) -> List[Policy]:
        """Get all active policies."""
        return [p for p in self.policies.values() if p.status == PolicyStatus.ACTIVE]
    
    def get_compliance_record(self, record_id: str) -> Optional[PolicyCompliance]:
        """Get a compliance record by ID."""
        return self.compliance_records.get(record_id)
    
    def get_policy_statistics(self) -> Dict[str, Any]:
        """Get statistics about policies."""
        total_policies = len(self.policies)
        active_policies = len(self.get_active_policies())
        
        by_type = {
            policy_type.value: len(self.get_policies_by_type(policy_type))
            for policy_type in PolicyType
        }
        
        total_compliance_checks = len(self.compliance_records)
        compliant_checks = sum(1 for r in self.compliance_records.values() if r.compliant)
        
        return {
            "total_policies": total_policies,
            "active_policies": active_policies,
            "by_type": by_type,
            "total_compliance_checks": total_compliance_checks,
            "compliance_rate": compliant_checks / total_compliance_checks if total_compliance_checks > 0 else 0.0,
        }
