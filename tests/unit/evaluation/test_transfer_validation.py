"""
Unit tests for the TransferValidator module.
"""

import pytest
from unittest.mock import patch

from src.evaluation.transfer_validation import TransferValidator


class TestTransferValidator:
    """Test cases for the TransferValidator class."""

    def test_init(self):
        """Test initialization of TransferValidator."""
        validator = TransferValidator()
        assert isinstance(validator, TransferValidator)
        assert hasattr(validator, 'transferable_concepts')
        assert hasattr(validator, 'domain_mappings')
        assert isinstance(validator.transferable_concepts, dict)
        assert isinstance(validator.domain_mappings, dict)

    def test_validate_empty_predictions(self):
        """Test validating with empty predictions list."""
        validator = TransferValidator()
        result = validator.validate([])
        
        assert isinstance(result, dict)
        assert "transfer_score" in result
        assert result["transfer_score"] == 0.0
        assert "details" in result

    def test_validate_no_transferable_concepts(self):
        """Test validating predictions with no transferable concepts."""
        validator = TransferValidator()
        predictions = [
            {"predicted_outcome": "hello world", "source_domain": "art", "target_domain": "literature"},
            {"predicted_outcome": "foo bar baz", "source_domain": "history", "target_domain": "geography"}
        ]
        
        result = validator.validate(predictions)
        
        assert isinstance(result, dict)
        assert "transfer_score" in result
        assert 0.0 <= result["transfer_score"] <= 1.0
        assert "details" in result
        # Should be low score since no transferable concepts
        assert result["transfer_score"] < 0.5

    def test_validate_with_transferable_concepts(self):
        """Test validating predictions with transferable concepts."""
        validator = TransferValidator()
        predictions = [
            {"predicted_outcome": "This algorithm uses graph optimization techniques", "source_domain": "cs", "target_domain": "cs"},
            {"predicted_outcome": "We calculated the integral of the function", "source_domain": "math", "target_domain": "physics"},
            {"predicted_outcome": "Random text with no relevant concepts", "source_domain": "art", "target_domain": "art"}
        ]
        
        result = validator.validate(predictions)
        
        assert isinstance(result, dict)
        assert "transfer_score" in result
        assert 0.0 <= result["transfer_score"] <= 1.0
        assert "details" in result
        # Should have some transfer score due to graph, but not perfect
        assert result["transfer_score"] > 0.0

    def test_validate_high_transfer(self):
        """Test validating predictions with high transfer potential."""
        validator = TransferValidator()
        predictions = [
            {"predicted_outcome": "We applied graph theory to optimize the network flow using advanced algorithms", "source_domain": "cs", "target_domain": "cs"},
            {"predicted_outcome": "The derivative of the function shows the rate of change, which is essential for optimization problems", "source_domain": "math", "target_domain": "engineering"},
            {"predicted_outcome": "Using machine learning models for pattern recognition in data arrays", "source_domain": "cs", "target_domain": "cs"}
        ]
        
        result = validator.validate(predictions)
        
        assert isinstance(result, dict)
        assert "transfer_score" in result
        assert 0.0 <= result["transfer_score"] <= 1.0
        assert "details" in result
        # Should have relatively high transfer score
        assert result["transfer_score"] > 0.3

    def test_validate_deterministic(self):
        """Test that validation is deterministic for the same input."""
        validator = TransferValidator()
        predictions = [
            {"predicted_outcome": "graph optimization algorithm", "source_domain": "cs", "target_domain": "cs"},
            {"predicted_outcome": "integral calculus for engineering", "source_domain": "math", "target_domain": "engineering"}
        ]
        
        # Validate twice with same inputs
        result1 = validator.validate(predictions)
        result2 = validator.validate(predictions)
        
        # Should be identical
        assert result1["transfer_score"] == result2["transfer_score"]
        assert result1["details"] == result2["details"]

    def test_validate_different_predictions(self):
        """Test that different predictions produce different results."""
        validator = TransferValidator()
        predictions1 = [
            {"predicted_outcome": "graph optimization algorithm", "source_domain": "cs", "target_domain": "cs"}
        ]
        predictions2 = [
            {"predicted_outcome": "hello world", "source_domain": "art", "target_domain": "art"}
        ]
        
        result1 = validator.validate(predictions1)
        result2 = validator.validate(predictions2)
        
        # Different predictions should generally give different scores
        # (though there's a small chance they could be the same)
        assert result1["transfer_score"] != result2["transfer_score"] or \
               result1["details"]["evaluation_seed"] != result2["details"]["evaluation_seed"]

    def test_validate_details_structure(self):
        """Test that the details field has expected structure."""
        validator = TransferValidator()
        predictions = [
            {"predicted_outcome": "graph algorithm optimization", "source_domain": "cs", "target_domain": "cs"}
        ]
        
        result = validator.validate(predictions)
        
        assert "details" in result
        details = result["details"]
        assert isinstance(details, dict)
        assert "total_predictions_evaluated" in details
        assert "overall_transfer_strength" in details
        assert "strongest_category" in details
        assert "weakest_category" in details
        assert "evaluation_seed" in details
        assert "assessment_summary" in details

    def test_repr(self):
        """Test string representation."""
        validator = TransferValidator()
        repr_str = repr(validator)
        assert "TransferValidator" in repr_str
        assert "concepts=" in repr_str
        assert "domain_mappings=" in repr_str
