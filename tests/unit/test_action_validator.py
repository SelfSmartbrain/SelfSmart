"""
Unit tests for ActionValidator - Phase 7: Safety & Governance Gate Hardening
"""

import pytest
from src.safety.action_validator import ActionValidator, ValidationResult


class TestActionValidator:
    """Test ActionValidator"""
    
    @pytest.fixture
    def validator(self):
        return ActionValidator()
    
    def test_allow_weight_fine_tune_within_bounds(self, validator):
        """Test weight_fine_tune action with valid parameters"""
        action = {
            "type": "weight_fine_tune",
            "epochs": 5,
            "learning_rate": 1e-4,
            "batch_size": 16,
        }
        
        result = validator.validate_action(action)
        
        assert result.allowed is True
        assert result.reason == "Action allowed"
    
    def test_allow_adapter_load(self, validator):
        """Test adapter_load action"""
        action = {
            "type": "adapter_load",
            "adapter_path": "data/adapters/requirement_adapter",
        }
        
        result = validator.validate_action(action)
        
        assert result.allowed is True
        assert result.reason == "Action allowed"
    
    def test_reject_weight_fine_tune_excessive_epochs(self, validator):
        """Test weight_fine_tune with epochs > MAX_EPOCHS is rejected"""
        action = {
            "type": "weight_fine_tune",
            "epochs": 15,  # Exceeds MAX_EPOCHS=10
            "learning_rate": 1e-4,
        }
        
        result = validator.validate_action(action)
        
        assert result.allowed is False
        assert "exceeds maximum allowed 10" in result.reason
    
    def test_reject_weight_fine_tune_excessive_learning_rate(self, validator):
        """Test weight_fine_tune with learning_rate > MAX_LEARNING_RATE is rejected"""
        action = {
            "type": "weight_fine_tune",
            "epochs": 3,
            "learning_rate": 5e-3,  # Exceeds MAX_LEARNING_RATE=1e-3
        }
        
        result = validator.validate_action(action)
        
        assert result.allowed is False
        assert "exceeds maximum allowed 0.001" in result.reason
    
    def test_reject_weight_fine_tune_excessive_batch_size(self, validator):
        """Test weight_fine_tune with batch_size > MAX_BATCH_SIZE is rejected"""
        action = {
            "type": "weight_fine_tune",
            "epochs": 3,
            "learning_rate": 1e-4,
            "batch_size": 64,  # Exceeds MAX_BATCH_SIZE=32
        }
        
        result = validator.validate_action(action)
        
        assert result.allowed is False
        assert "exceeds maximum allowed 32" in result.reason
    
    def test_reject_blocked_action_types(self, validator):
        """Test that blocked action types are rejected"""
        for blocked_type in ["delete_file", "write_file", "shell_command", "self_modify", "deploy"]:
            action = {"type": blocked_type}
            result = validator.validate_action(action)
            assert result.allowed is False
            assert "requires explicit approval" in result.reason
    
    def test_reject_blocked_terms(self, validator):
        """Test that blocked terms in payload are rejected"""
        action = {"type": "execute_task", "payload": "rm -rf /"}
        result = validator.validate_action(action)
        
        assert result.allowed is False
        assert "blocked operation" in result.reason
    
    def test_allow_safe_action_types(self, validator):
        """Test that safe action types are allowed"""
        for safe_type in ["observe", "think", "reflect", "plan", "research", "memory_consolidation", "execute_task"]:
            action = {"type": safe_type}
            result = validator.validate_action(action)
            assert result.allowed is True
    
    def test_unknown_action_type_allowed_with_warning(self, validator):
        """Test unknown action type is allowed with caution warning"""
        action = {"type": "unknown_action"}
        result = validator.validate_action(action)
        
        assert result.allowed is True
        assert "caution" in result.reason
        assert "Unknown action type 'unknown_action'" in result.warnings
    
    def test_none_action_rejected(self, validator):
        """Test None action is rejected"""
        result = validator.validate_action(None)
        
        assert result.allowed is False
        assert "empty" in result.reason
    
    def test_string_action_type(self, validator):
        """Test string action type is handled"""
        result = validator.validate_action("plan")
        
        assert result.allowed is True
        assert result.reason == "Action allowed"


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_bool_true(self):
        """Test ValidationResult with allowed=True evaluates to True"""
        result = ValidationResult(allowed=True, reason="OK")
        assert bool(result) is True
    
    def test_bool_false(self):
        """Test ValidationResult with allowed=False evaluates to False"""
        result = ValidationResult(allowed=False, reason="Blocked")
        assert bool(result) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])