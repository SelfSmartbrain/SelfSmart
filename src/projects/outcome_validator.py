from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ValidationResult(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    target_id: uuid.UUID
    is_valid: bool
    feedback: List[str]
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class OutcomeValidator:
    def __init__(self):
        # Define validation criteria for different target types
        self.validation_criteria = {
            "project": ["completion_rate", "quality_score", "stakeholder_satisfaction"],
            "task": ["completion_status", "quality_metrics", "timeliness"],
            "research": ["novelty_score", "validity_score", "reproducibility"],
            "code": ["test_coverage", "code_quality", "performance_metrics"],
        }

    async def validate_outcome(self, target_id: uuid.UUID, outcome_data: dict) -> ValidationResult:
        logger.info(f"Validating outcome for target {target_id}")

        # Extract target type from outcome_data or use default
        target_type = outcome_data.get("target_type", "unknown")

        # Get relevant criteria for this target type
        criteria = self.validation_criteria.get(target_type, ["completeness", "accuracy"])

        # Initialize validation results
        is_valid = True
        feedback = []
        failed_criteria = []

        # Check each criterion
        for criterion in criteria:
            if criterion not in outcome_data:
                is_valid = False
                failed_criteria.append(f"Missing required metric: {criterion}")
                continue

            value = outcome_data[criterion]

            # Apply validation rules based on criterion type
            if isinstance(value, (int, float)):
                if value < 0:
                    is_valid = False
                    failed_criteria.append(f"Invalid negative value for {criterion}: {value}")
                elif (
                    criterion.endswith("_rate")
                    or criterion.endswith("_score")
                    or criterion.endswith("_percentage")
                ):
                    # Assume these should be between 0 and 100 or 0 and 1
                    if value < 0 or (value > 1 and value > 100):
                        is_valid = False
                        failed_criteria.append(
                            f"Value out of expected range for {criterion}: {value}"
                        )
            elif isinstance(value, str):
                if not value.strip():
                    is_valid = False
                    failed_criteria.append(f"Empty value for {criterion}")
            elif value is None:
                is_valid = False
                failed_criteria.append(f"Null value for {criterion}")

        # Generate feedback based on validation results
        if is_valid:
            feedback.append(f"All validation criteria met for {target_type}")
            feedback.append(f"Overall outcome quality: satisfactory")
        else:
            feedback.append(f"Validation failed for {target_type}")
            feedback.extend(failed_criteria)
            if len(failed_criteria) <= 2:  # Only show specific failures if not too many
                feedback.append(f"Failed criteria: {', '.join(failed_criteria)}")

        # Add overall assessment
        if outcome_data.get("overall_score", 0) >= 80:
            feedback.append("Overall outcome exceeds expectations")
        elif outcome_data.get("overall_score", 0) >= 60:
            feedback.append("Overall outcome meets minimum requirements")
        else:
            feedback.append("Overall outcome requires improvement")
            is_valid = False

        return ValidationResult(target_id=target_id, is_valid=is_valid, feedback=feedback)
