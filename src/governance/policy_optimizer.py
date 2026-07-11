"""policy_optimizer.py

Phase 16F: Policy Optimizer

Optimizes governance policies based on decision outcomes.
Implements:
- Policy effectiveness analysis
- Policy parameter tuning
- Policy conflict resolution
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class OptimizationType(str, Enum):
    """Types of policy optimization."""
    PARAMETER_TUNING = "parameter_tuning"
    SCOPE_ADJUSTMENT = "scope_adjustment"
    RULE_MODIFICATION = "rule_modification"
    POLICY_MERGING = "policy_merging"
    POLICY_RETIREMENT = "policy_retirement"


@dataclass
class PolicyOptimization:
    """An optimization proposal for a policy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str = ""
    optimization_type: OptimizationType = OptimizationType.PARAMETER_TUNING
    description: str = ""
    current_policy: Dict[str, Any] = field(default_factory=dict)
    optimized_policy: Dict[str, Any] = field(default_factory=dict)
    expected_improvement: float = 0.0
    rationale: str = ""
    status: str = "proposed"  # proposed, approved, rejected
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "optimization_type": self.optimization_type.value,
            "description": self.description,
            "current_policy": self.current_policy,
            "optimized_policy": self.optimized_policy,
            "expected_improvement": self.expected_improvement,
            "rationale": self.rationale,
            "status": self.status,
            "metadata": self.metadata,
        }


class PolicyOptimizer:
    """Optimizes governance policies."""
    
    def __init__(self):
        self.optimizations: Dict[str, PolicyOptimization] = {}
        self.policy_performance: Dict[str, Dict[str, Any]] = {}
        logger.info("PolicyOptimizer initialized")
    
    def analyze_policy_effectiveness(
        self,
        policy_id: str,
        compliance_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze the effectiveness of a policy."""
        if not compliance_records:
            return {"error": "No compliance records available"}
        
        # Calculate compliance rate
        compliant = sum(1 for r in compliance_records if r.get("compliant", False))
        total = len(compliance_records)
        compliance_rate = compliant / total if total > 0 else 0.0
        
        # Calculate violation patterns
        violations = []
        for record in compliance_records:
            if not record.get("compliant", False):
                violations.extend(record.get("violations", []))
        
        from collections import Counter
        violation_counts = Counter(violations)
        
        performance = {
            "policy_id": policy_id,
            "compliance_rate": compliance_rate,
            "total_checks": total,
            "compliant_checks": compliant,
            "violation_counts": dict(violation_counts.most_common(5)),
            "most_common_violation": violation_counts.most_common(1)[0] if violation_counts else None,
        }
        
        self.policy_performance[policy_id] = performance
        
        return performance
    
    def propose_optimization(
        self,
        policy_id: str,
        current_policy: Dict[str, Any],
        performance: Optional[Dict[str, Any]] = None,
    ) -> Optional[PolicyOptimization]:
        """Propose an optimization for a policy."""
        if performance is None:
            performance = self.policy_performance.get(policy_id)
        
        if performance is None:
            logger.warning(f"No performance data for policy {policy_id}")
            return None
        
        compliance_rate = performance.get("compliance_rate", 0.0)
        
        # Only propose optimization if compliance is low
        if compliance_rate > 0.8:
            logger.info(f"Policy {policy_id} has good compliance, no optimization needed")
            return None
        
        optimization = None
        
        # Determine optimization type based on issues
        most_common_violation = performance.get("most_common_violation")
        
        if most_common_violation:
            violation_type, count = most_common_violation
            
            if "risk" in violation_type.lower():
                optimization = self._propose_risk_parameter_tuning(policy_id, current_policy, performance)
            elif "resource" in violation_type.lower():
                optimization = self._propose_resource_adjustment(policy_id, current_policy, performance)
            else:
                optimization = self._propose_scope_adjustment(policy_id, current_policy, performance)
        
        if optimization:
            self.optimizations[optimization.id] = optimization
            logger.info(f"Proposed optimization for policy {policy_id}")
        
        return optimization
    
    def _propose_risk_parameter_tuning(
        self,
        policy_id: str,
        current_policy: Dict[str, Any],
        performance: Dict[str, Any],
    ) -> PolicyOptimization:
        """Propose risk parameter tuning."""
        rules = current_policy.get("rules", [])
        
        optimized_policy = current_policy.copy()
        optimized_rules = []
        
        for rule in rules:
            if rule.get("type") == "risk_limit":
                # Increase risk limit by 20%
                params = rule.get("parameters", {})
                current_limit = params.get("max_risk", 1.0)
                new_limit = min(1.0, current_limit * 1.2)
                params["max_risk"] = new_limit
                rule["parameters"] = params
            
            optimized_rules.append(rule)
        
        optimized_policy["rules"] = optimized_rules
        
        return PolicyOptimization(
            policy_id=policy_id,
            optimization_type=OptimizationType.PARAMETER_TUNING,
            description="Increase risk limit to improve compliance",
            current_policy=current_policy,
            optimized_policy=optimized_policy,
            expected_improvement=0.2,
            rationale="Current risk limit is too strict, causing frequent violations",
        )
    
    def _propose_resource_adjustment(
        self,
        policy_id: str,
        current_policy: Dict[str, Any],
        performance: Dict[str, Any],
    ) -> PolicyOptimization:
        """Propose resource requirement adjustment."""
        rules = current_policy.get("rules", [])
        
        optimized_policy = current_policy.copy()
        optimized_rules = []
        
        for rule in rules:
            if rule.get("type") == "resource_requirement":
                # Decrease minimum requirement by 20%
                params = rule.get("parameters", {})
                current_min = params.get("min_amount", 0)
                new_min = max(0, current_min * 0.8)
                params["min_amount"] = new_min
                rule["parameters"] = params
            
            optimized_rules.append(rule)
        
        optimized_policy["rules"] = optimized_rules
        
        return PolicyOptimization(
            policy_id=policy_id,
            optimization_type=OptimizationType.PARAMETER_TUNING,
            description="Reduce resource requirement to improve compliance",
            current_policy=current_policy,
            optimized_policy=optimized_policy,
            expected_improvement=0.2,
            rationale="Current resource requirements are too high, causing frequent violations",
        )
    
    def _propose_scope_adjustment(
        self,
        policy_id: str,
        current_policy: Dict[str, Any],
        performance: Dict[str, Any],
    ) -> PolicyOptimization:
        """Propose scope adjustment."""
        scope = current_policy.get("scope", [])
        
        optimized_policy = current_policy.copy()
        
        # Narrow scope to reduce violations
        if len(scope) > 1:
            optimized_policy["scope"] = scope[:-1]
        
        return PolicyOptimization(
            policy_id=policy_id,
            optimization_type=OptimizationType.SCOPE_ADJUSTMENT,
            description="Narrow policy scope to reduce violations",
            current_policy=current_policy,
            optimized_policy=optimized_policy,
            expected_improvement=0.15,
            rationale="Policy scope is too broad, causing violations in edge cases",
        )
    
    def detect_policy_conflicts(
        self,
        policies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between policies."""
        conflicts = []
        
        for i, policy1 in enumerate(policies):
            for policy2 in policies[i+1:]:
                conflict = self._check_policy_conflict(policy1, policy2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_policy_conflict(
        self,
        policy1: Dict[str, Any],
        policy2: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Check if two policies conflict."""
        rules1 = policy1.get("rules", [])
        rules2 = policy2.get("rules", [])
        
        # Check for conflicting risk limits
        risk_limits1 = [r.get("parameters", {}).get("max_risk") for r in rules1 if r.get("type") == "risk_limit"]
        risk_limits2 = [r.get("parameters", {}).get("max_risk") for r in rules2 if r.get("type") == "risk_limit"]
        
        if risk_limits1 and risk_limits2:
            if abs(risk_limits1[0] - risk_limits2[0]) > 0.3:
                return {
                    "policy1_id": policy1.get("id"),
                    "policy2_id": policy2.get("id"),
                    "conflict_type": "risk_limit_mismatch",
                    "description": f"Conflicting risk limits: {risk_limits1[0]} vs {risk_limits2[0]}",
                }
        
        return None
    
    def propose_policy_merge(
        self,
        policy1: Dict[str, Any],
        policy2: Dict[str, Any],
    ) -> Optional[PolicyOptimization]:
        """Propose merging two policies."""
        if policy1.get("policy_type") != policy2.get("policy_type"):
            logger.warning("Cannot merge policies of different types")
            return None
        
        merged_policy = {
            "name": f"{policy1.get('name')} + {policy2.get('name')}",
            "policy_type": policy1.get("policy_type"),
            "rules": policy1.get("rules", []) + policy2.get("rules", []),
            "scope": list(set(policy1.get("scope", [])) | set(policy2.get("scope", []))),
        }
        
        return PolicyOptimization(
            policy_id=f"merged_{policy1.get('id')}_{policy2.get('id')}",
            optimization_type=OptimizationType.POLICY_MERGING,
            description=f"Merge {policy1.get('name')} and {policy2.get('name')}",
            current_policy={"policy1": policy1, "policy2": policy2},
            optimized_policy=merged_policy,
            expected_improvement=0.1,
            rationale="Policies have similar scope and can be consolidated",
        )
    
    def get_optimization(self, optimization_id: str) -> Optional[PolicyOptimization]:
        """Get an optimization by ID."""
        return self.optimizations.get(optimization_id)
    
    def get_policy_performance(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get performance data for a policy."""
        return self.policy_performance.get(policy_id)
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get statistics about optimizations."""
        total_optimizations = len(self.optimizations)
        
        by_type = {
            opt_type.value: len([o for o in self.optimizations.values() if o.optimization_type == opt_type])
            for opt_type in OptimizationType
        }
        
        return {
            "total_optimizations": total_optimizations,
            "by_type": by_type,
            "policies_analyzed": len(self.policy_performance),
        }
