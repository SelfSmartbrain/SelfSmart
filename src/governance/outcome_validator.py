"""outcome_validator.py

Phase 16H: Outcome Validator

Validates that outcomes match predictions.
Checks:
- Prediction accuracy
- Outcome completeness
- Measurement validity
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ValidationStatus(str, Enum):
    """Status of outcome validation."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"


@dataclass
class ValidationCheck:
    """A single validation check."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    check_type: str = ""
    passed: bool = False
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "check_type": self.check_type,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class OutcomeValidation:
    """Validation of decision outcomes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    predicted_outcome: Dict[str, Any] = field(default_factory=dict)
    actual_outcome: Dict[str, Any] = field(default_factory=dict)
    checks: List[ValidationCheck] = field(default_factory=list)
    status: ValidationStatus = ValidationStatus.PENDING
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    overall_score: float = 0.0
    discrepancies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "predicted_outcome": self.predicted_outcome,
            "actual_outcome": self.actual_outcome,
            "checks": [c.to_dict() for c in self.checks],
            "status": self.status.value,
            "accuracy_score": self.accuracy_score,
            "completeness_score": self.completeness_score,
            "overall_score": self.overall_score,
            "discrepancies": self.discrepancies,
            "metadata": self.metadata,
        }


class OutcomeValidator:
    """Validates decision outcomes against predictions."""
    
    def __init__(self):
        self.validations: Dict[str, OutcomeValidation] = {}
        self.validations_by_decision: Dict[str, str] = {}  # decision_id -> validation_id
        logger.info("OutcomeValidator initialized")
    
    def validate_outcome(
        self,
        decision_id: str,
        predicted_outcome: Dict[str, Any],
        actual_outcome: Dict[str, Any],
    ) -> OutcomeValidation:
        """Validate an actual outcome against predictions."""
        validation = OutcomeValidation(
            decision_id=decision_id,
            predicted_outcome=predicted_outcome,
            actual_outcome=actual_outcome,
        )
        
        # Run validation checks
        validation.checks = [
            self._check_completeness(predicted_outcome, actual_outcome),
            self._check_accuracy(predicted_outcome, actual_outcome),
            self._check_consistency(predicted_outcome, actual_outcome),
            self._check_reasonableness(actual_outcome),
        ]
        
        # Calculate scores
        validation.completeness_score = self._calculate_completeness_score(validation.checks)
        validation.accuracy_score = self._calculate_accuracy_score(validation.checks)
        validation.overall_score = (validation.completeness_score + validation.accuracy_score) / 2
        
        # Determine status
        validation.status = self._determine_status(validation)
        
        # Identify discrepancies
        validation.discrepancies = self._identify_discrepancies(predicted_outcome, actual_outcome)
        
        # Store validation
        self.validations[validation.id] = validation
        self.validations_by_decision[decision_id] = validation.id
        
        logger.info(f"Validated outcome for decision {decision_id}: {validation.status.value}")
        
        return validation
    
    def _check_completeness(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> ValidationCheck:
        """Check if actual outcome has all expected metrics."""
        check = ValidationCheck(check_type="completeness")
        
        predicted_keys = set(predicted.keys())
        actual_keys = set(actual.keys())
        
        missing_keys = predicted_keys - actual_keys
        extra_keys = actual_keys - predicted_keys
        
        if missing_keys:
            check.passed = False
            check.message = f"Missing expected metrics: {missing_keys}"
            check.details = {"missing_keys": list(missing_keys)}
        elif extra_keys:
            check.passed = True
            check.message = f"All expected metrics present, with extras: {extra_keys}"
            check.details = {"extra_keys": list(extra_keys)}
        else:
            check.passed = True
            check.message = "All expected metrics present"
        
        return check
    
    def _check_accuracy(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> ValidationCheck:
        """Check if actual values match predicted values within tolerance."""
        check = ValidationCheck(check_type="accuracy")
        
        common_keys = set(predicted.keys()) & set(actual.keys())
        
        if not common_keys:
            check.passed = False
            check.message = "No common metrics to compare"
            return check
        
        discrepancies = []
        tolerance = 0.1  # 10% tolerance
        
        for key in common_keys:
            pred_val = predicted[key]
            act_val = actual[key]
            
            # Handle numeric values
            if isinstance(pred_val, (int, float)) and isinstance(act_val, (int, float)):
                if pred_val != 0:
                    diff = abs(pred_val - act_val) / abs(pred_val)
                    if diff > tolerance:
                        discrepancies.append(f"{key}: predicted {pred_val}, actual {act_val}")
                else:
                    if act_val != 0:
                        discrepancies.append(f"{key}: predicted 0, actual {act_val}")
            # Handle string values
            elif isinstance(pred_val, str) and isinstance(act_val, str):
                if pred_val.lower() != act_val.lower():
                    discrepancies.append(f"{key}: predicted '{pred_val}', actual '{act_val}'")
        
        if discrepancies:
            check.passed = False
            check.message = f"Accuracy discrepancies found: {len(discrepancies)}"
            check.details = {"discrepancies": discrepancies}
        else:
            check.passed = True
            check.message = "All values within tolerance"
        
        return check
    
    def _check_consistency(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> ValidationCheck:
        """Check for internal consistency in outcomes."""
        check = ValidationCheck(check_type="consistency")
        
        # Simple consistency check - in production, use more sophisticated validation
        issues = []
        
        # Check for negative values where positive expected
        for key, value in actual.items():
            if isinstance(value, (int, float)) and value < 0:
                if "cost" not in key.lower() and "loss" not in key.lower():
                    issues.append(f"Unexpected negative value for {key}: {value}")
        
        if issues:
            check.passed = False
            check.message = f"Consistency issues found: {len(issues)}"
            check.details = {"issues": issues}
        else:
            check.passed = True
            check.message = "Outcome is internally consistent"
        
        return check
    
    def _check_reasonableness(self, actual: Dict[str, Any]) -> ValidationCheck:
        """Check if outcome values are reasonable."""
        check = ValidationCheck(check_type="reasonableness")
        
        issues = []
        
        # Check for extreme values
        for key, value in actual.items():
            if isinstance(value, (int, float)):
                if abs(value) > 1e6:  # Very large values
                    issues.append(f"Extreme value for {key}: {value}")
                if abs(value) < 1e-10 and value != 0:  # Very small non-zero values
                    issues.append(f"Very small value for {key}: {value}")
        
        if issues:
            check.passed = False
            check.message = f"Unreasonable values found: {len(issues)}"
            check.details = {"issues": issues}
        else:
            check.passed = True
            check.message = "All values are reasonable"
        
        return check
    
    def _calculate_completeness_score(self, checks: List[ValidationCheck]) -> float:
        """Calculate completeness score from checks."""
        completeness_check = next((c for c in checks if c.check_type == "completeness"), None)
        
        if completeness_check:
            return 1.0 if completeness_check.passed else 0.5
        
        return 0.5
    
    def _calculate_accuracy_score(self, checks: List[ValidationCheck]) -> float:
        """Calculate accuracy score from checks."""
        accuracy_check = next((c for c in checks if c.check_type == "accuracy"), None)
        
        if accuracy_check:
            if accuracy_check.passed:
                return 1.0
            else:
                # Partial credit based on number of discrepancies
                discrepancies = accuracy_check.details.get("discrepancies", [])
                if discrepancies:
                    return max(0.0, 1.0 - len(discrepancies) * 0.1)
        
        return 0.5
    
    def _determine_status(self, validation: OutcomeValidation) -> ValidationStatus:
        """Determine overall validation status."""
        passed_checks = sum(1 for c in validation.checks if c.passed)
        total_checks = len(validation.checks)
        
        if passed_checks == total_checks:
            return ValidationStatus.VALID
        elif passed_checks >= total_checks * 0.5:
            return ValidationStatus.PARTIAL
        elif validation.overall_score > 0.3:
            return ValidationStatus.UNCERTAIN
        else:
            return ValidationStatus.INVALID
    
    def _identify_discrepancies(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> List[str]:
        """Identify specific discrepancies between predicted and actual."""
        discrepancies = []
        
        common_keys = set(predicted.keys()) & set(actual.keys())
        
        for key in common_keys:
            pred_val = predicted[key]
            act_val = actual[key]
            
            if pred_val != act_val:
                discrepancies.append(f"{key}: predicted {pred_val}, actual {act_val}")
        
        return discrepancies
    
    def get_validation(self, validation_id: str) -> Optional[OutcomeValidation]:
        """Get a validation by ID."""
        return self.validations.get(validation_id)
    
    def get_validation_by_decision(self, decision_id: str) -> Optional[OutcomeValidation]:
        """Get validation by decision ID."""
        validation_id = self.validations_by_decision.get(decision_id)
        if validation_id:
            return self.validations.get(validation_id)
        return None
    
    def get_validations_by_status(self, status: ValidationStatus) -> List[OutcomeValidation]:
        """Get all validations with a specific status."""
        return [v for v in self.validations.values() if v.status == status]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get statistics about validations."""
        total_validations = len(self.validations)
        
        by_status = {
            status.value: len(self.get_validations_by_status(status))
            for status in ValidationStatus
        }
        
        avg_accuracy = (
            sum(v.accuracy_score for v in self.validations.values()) / total_validations
            if total_validations > 0 else 0.0
        )
        
        avg_completeness = (
            sum(v.completeness_score for v in self.validations.values()) / total_validations
            if total_validations > 0 else 0.0
        )
        
        return {
            "total_validations": total_validations,
            "by_status": by_status,
            "average_accuracy": avg_accuracy,
            "average_completeness": avg_completeness,
        }
