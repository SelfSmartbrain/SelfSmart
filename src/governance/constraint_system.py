"""constraint_system.py

Phase 16D: Constraint System

Manages constraints that govern decision-making.
Supports:
- Hard constraints (must be satisfied)
- Soft constraints (preferably satisfied)
- Ethical constraints
- Safety constraints
- Resource constraints
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ConstraintType(str, Enum):
    """Types of constraints."""
    HARD = "hard"
    SOFT = "soft"
    ETHICAL = "ethical"
    SAFETY = "safety"
    RESOURCE = "resource"
    LEGAL = "legal"


class ConstraintSeverity(str, Enum):
    """Severity of constraint violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Constraint:
    """A constraint on decision-making."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    constraint_type: ConstraintType = ConstraintType.HARD
    severity: ConstraintSeverity = ConstraintSeverity.HIGH
    condition: str = ""  # condition to check
    parameters: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    violation_count: int = 0
    last_violated: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "constraint_type": self.constraint_type.value,
            "severity": self.severity.value,
            "condition": self.condition,
            "parameters": self.parameters,
            "active": self.active,
            "violation_count": self.violation_count,
            "last_violated": self.last_violated,
            "metadata": self.metadata,
        }


@dataclass
class ConstraintViolation:
    """A record of a constraint violation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    constraint_id: str = ""
    decision_id: str = ""
    violation_type: str = ""
    severity: ConstraintSeverity = ConstraintSeverity.HIGH
    description: str = ""
    timestamp: str = ""
    resolved: bool = False
    resolution: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "constraint_id": self.constraint_id,
            "decision_id": self.decision_id,
            "violation_type": self.violation_type,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "metadata": self.metadata,
        }


class ConstraintSystem:
    """Manages constraints on decision-making."""
    
    def __init__(self):
        self.constraints: Dict[str, Constraint] = {}
        self.violations: Dict[str, ConstraintViolation] = {}
        logger.info("ConstraintSystem initialized")
    
    def add_constraint(
        self,
        name: str,
        description: str,
        constraint_type: ConstraintType,
        condition: str,
        parameters: Optional[Dict[str, Any]] = None,
        severity: ConstraintSeverity = ConstraintSeverity.HIGH,
    ) -> Constraint:
        """Add a new constraint."""
        constraint = Constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            condition=condition,
            parameters=parameters or {},
            severity=severity,
        )
        
        self.constraints[constraint.id] = constraint
        logger.info(f"Added constraint: {name}")
        
        return constraint
    
    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint."""
        if constraint_id in self.constraints:
            del self.constraints[constraint_id]
            logger.info(f"Removed constraint: {constraint_id}")
            return True
        return False
    
    def check_constraints(
        self,
        decision_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Check if a decision violates any constraints."""
        context = context or decision_data.get("context", {})
        
        violations = []
        passed = []
        
        for constraint in self.constraints.values():
            if not constraint.active:
                continue
            
            result = self._evaluate_constraint(constraint, decision_data, context)
            
            if not result["satisfied"]:
                violation = ConstraintViolation(
                    constraint_id=constraint.id,
                    decision_id=decision_data.get("id", ""),
                    violation_type=constraint.constraint_type.value,
                    severity=constraint.severity,
                    description=result["reason"],
                    timestamp=result["timestamp"],
                )
                self.violations[violation.id] = violation
                violations.append(violation)
                
                # Update constraint violation count
                constraint.violation_count += 1
                constraint.last_violated = result["timestamp"]
            else:
                passed.append(constraint.id)
        
        # Determine overall result
        hard_violations = [v for v in violations if v.severity in [ConstraintSeverity.CRITICAL, ConstraintSeverity.HIGH]]
        
        return {
            "decision_id": decision_data.get("id", ""),
            "passed": passed,
            "violations": [v.to_dict() for v in violations],
            "hard_violations": len(hard_violations) > 0,
            "approved": len(hard_violations) == 0,
        }
    
    def _evaluate_constraint(
        self,
        constraint: Constraint,
        decision_data: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate a single constraint."""
        from datetime import datetime, timezone
        
        # Simple evaluation - in production, use a proper expression evaluator
        satisfied = True
        reason = ""
        
        # Check resource constraints
        if constraint.constraint_type == ConstraintType.RESOURCE:
            resource_type = constraint.parameters.get("resource_type")
            min_required = constraint.parameters.get("min_required", 0)
            available = context.get("available_resources", {}).get(resource_type, 0)
            
            if available < min_required:
                satisfied = False
                reason = f"Insufficient {resource_type}: {available} < {min_required}"
        
        # Check risk constraints
        elif constraint.constraint_type == ConstraintType.SAFETY:
            max_risk = constraint.parameters.get("max_risk", 1.0)
            options = decision_data.get("options", [])
            selected_id = decision_data.get("selected_option_id")
            selected = next((opt for opt in options if opt.get("id") == selected_id), None)
            
            if selected and selected.get("risk_score", 0) > max_risk:
                satisfied = False
                reason = f"Risk exceeds safety limit: {selected.get('risk_score', 0)} > {max_risk}"
        
        # Check ethical constraints
        elif constraint.constraint_type == ConstraintType.ETHICAL:
            ethical_flags = decision_data.get("metadata", {}).get("ethical_flags", [])
            forbidden = constraint.parameters.get("forbidden_actions", [])
            
            for flag in ethical_flags:
                if any(f in flag.lower() for f in forbidden):
                    satisfied = False
                    reason = f"Ethical concern: {flag}"
                    break
        
        # Default: satisfied
        if satisfied:
            reason = "Constraint satisfied"
        
        return {
            "satisfied": satisfied,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def resolve_violation(
        self,
        violation_id: str,
        resolution: str,
    ) -> bool:
        """Resolve a constraint violation."""
        if violation_id in self.violations:
            self.violations[violation_id].resolved = True
            self.violations[violation_id].resolution = resolution
            logger.info(f"Resolved violation: {violation_id}")
            return True
        return False
    
    def get_constraint(self, constraint_id: str) -> Optional[Constraint]:
        """Get a constraint by ID."""
        return self.constraints.get(constraint_id)
    
    def get_constraints_by_type(self, constraint_type: ConstraintType) -> List[Constraint]:
        """Get all constraints of a specific type."""
        return [c for c in self.constraints.values() if c.constraint_type == constraint_type]
    
    def get_active_constraints(self) -> List[Constraint]:
        """Get all active constraints."""
        return [c for c in self.constraints.values() if c.active]
    
    def get_violation(self, violation_id: str) -> Optional[ConstraintViolation]:
        """Get a violation by ID."""
        return self.violations.get(violation_id)
    
    def get_violations_by_constraint(self, constraint_id: str) -> List[ConstraintViolation]:
        """Get all violations for a constraint."""
        return [v for v in self.violations.values() if v.constraint_id == constraint_id]
    
    def get_constraint_statistics(self) -> Dict[str, Any]:
        """Get statistics about constraints."""
        total_constraints = len(self.constraints)
        active_constraints = len(self.get_active_constraints())
        
        by_type = {
            constraint_type.value: len(self.get_constraints_by_type(constraint_type))
            for constraint_type in ConstraintType
        }
        
        total_violations = len(self.violations)
        unresolved_violations = sum(1 for v in self.violations.values() if not v.resolved)
        
        return {
            "total_constraints": total_constraints,
            "active_constraints": active_constraints,
            "by_type": by_type,
            "total_violations": total_violations,
            "unresolved_violations": unresolved_violations,
        }
