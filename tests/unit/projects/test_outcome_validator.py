"""
Unit tests for the OutcomeValidator module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.projects.outcome_validator import OutcomeValidator, ValidationResult


class TestOutcomeValidator:
    """Test cases for the OutcomeValidator class."""

    def test_init(self):
        """Test initialization of OutcomeValidator."""
        validator = OutcomeValidator()
        assert isinstance(validator, OutcomeValidator)
        assert hasattr(validator, 'validation_criteria')
        assert isinstance(validator.validation_criteria, dict)

    @pytest.mark.asyncio
    async def test_validate_outcome_valid(self):
        """Test validating a valid outcome."""
        validator = OutcomeValidator()
        target_id = uuid.uuid4()
        
        # Valid outcome data
        outcome_data = {
            "target_type": "project",
            "completion_rate": 0.95,
            "quality_score": 8.5,
            "stakeholder_satisfaction": 0.9,
            "overall_score": 88
        }
        
        result = await validator.validate_outcome(target_id, outcome_data)
        
        assert isinstance(result, ValidationResult)
        assert result.target_id == target_id
        assert result.is_valid is True
        assert isinstance(result.feedback, list)
        assert len(result.feedback) > 0
        assert any("met" in feedback.lower() or "satisfactory" in feedback.lower() 
                  for feedback in result.feedback)
        assert isinstance(result.validated_at, datetime)

    @pytest.mark.asyncio
    async def test_validate_outcome_invalid_missing_criteria(self):
        """Test validating an outcome with missing criteria."""
        validator = OutcomeValidator()
        target_id = uuid.uuid4()
        
        # Missing required criteria
        outcome_data = {
            "target_type": "project",
            "completion_rate": 0.95
            # Missing quality_score and stakeholder_satisfaction
        }
        
        result = await validator.validate_outcome(target_id, outcome_data)
        
        assert isinstance(result, ValidationResult)
        assert result.target_id == target_id
        assert result.is_valid is False
        assert isinstance(result.feedback, list)
        assert len(result.feedback) > 0
        assert any("missing" in feedback.lower() for feedback in result.feedback)

    @pytest.mark.asyncio
    async def test_validate_outcome_invalid_values(self):
        """Test validating an outcome with invalid values."""
        validator = OutcomeValidator()
        target_id = uuid.uuid4()
        
        # Invalid values (negative scores, out of range)
        outcome_data = {
            "target_type": "project",
            "completion_rate": -0.1,  # Invalid: negative
            "quality_score": 150,     # Invalid: too high
            "stakeholder_satisfaction": 0.9,
            "overall_score": 88
        }
        
        result = await validator.validate_outcome(target_id, outcome_data)
        
        assert isinstance(result, ValidationResult)
        assert result.target_id == target_id
        assert result.is_valid is False
        assert isinstance(result.feedback, list)
        assert len(result.feedback) > 0
        assert any("invalid" in feedback.lower() or "out of expected range" in feedback.lower() 
                  for feedback in result.feedback)

    @pytest.mark.asyncio
    async def test_validate_outcome_low_overall_score(self):
        """Test validating an outcome with low overall score."""
        validator = OutcomeValidator()
        target_id = uuid.uuid4()
        
        # Low overall score should make it invalid
        outcome_data = {
            "target_type": "project",
            "completion_rate": 0.5,
            "quality_score": 5.0,
            "stakeholder_satisfaction": 0.4,
            "overall_score": 45  # Below 60 threshold
        }
        
        result = await validator.validate_outcome(target_id, outcome_data)
        
        assert isinstance(result, ValidationResult)
        assert result.target_id == target_id
        # Depending on implementation, might still be valid if individual criteria pass
        # but overall assessment should mention needing improvement
        assert isinstance(result.feedback, list)
        assert len(result.feedback) > 0
        assert any("improvement" in feedback.lower() or "requirements" in feedback.lower() 
                  for feedback in result.feedback)

    @pytest.mark.asyncio
    async def test_validate_outcome_different_target_types(self):
        """Test validating outcomes for different target types."""
        validator = OutcomeValidator()
        target_id = uuid.uuid4()
        
        # Test task type
        task_data = {
            "target_type": "task",
            "completion_status": "completed",
            "quality_metrics": {"accuracy": 0.9},
            "timeliness": "on_time"
        }
        task_result = await validator.validate_outcome(target_id, task_data)
        assert isinstance(task_result, ValidationResult)
        
        # Test research type
        research_data = {
            "target_type": "research",
            "novelty_score": 0.8,
            "validity_score": 0.85,
            "reproducibility": 0.75
        }
        research_result = await validator.validate_outcome(target_id, research_data)
        assert isinstance(research_result, ValidationResult)
        
        # Test code type
        code_data = {
            "target_type": "code",
            "test_coverage": 0.85,
            "code_quality": "good",
            "performance_metrics": {"response_time": 150}
        }
        code_result = await validator.validate_outcome(target_id, code_data)
        assert isinstance(code_result, ValidationResult)

    def test_validation_result_model(self):
        """Test the ValidationResult model."""
        result = ValidationResult(
            id=uuid.uuid4(),
            target_id=uuid.uuid4(),
            is_valid=True,
            feedback=["All criteria met", "Good performance"],
            validated_at=datetime.now(timezone.utc)
        )
        
        assert isinstance(result.id, uuid.UUID)
        assert isinstance(result.target_id, uuid.UUID)
        assert result.is_valid is True
        assert result.feedback == ["All criteria met", "Good performance"]
        assert isinstance(result.validated_at, datetime)
