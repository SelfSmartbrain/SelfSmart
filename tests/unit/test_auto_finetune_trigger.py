"""
Unit tests for AutoFineTuneTrigger - Phase 8: Requirement Feedback & Automated Fine-Tune Triggering
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.learning.auto_finetune_trigger import (
    AutoFineTuneTrigger,
    AutoFineTuneConfig,
    FineTuneTriggerRecord,
    create_auto_finetune_trigger,
)


class TestAutoFineTuneConfig:
    """Test AutoFineTuneConfig dataclass"""
    
    def test_default_config(self):
        config = AutoFineTuneConfig()
        assert config.evaluation_threshold == 0.8
        assert config.max_auto_finetune_epochs == 3
        assert config.auto_finetune_learning_rate == 2e-4
        assert config.adapter_save_path == "data/adapters/requirement_adapter"
        assert config.require_safety_approval is True
        assert config.max_concurrent_finetunes == 1
    
    def test_custom_config(self):
        config = AutoFineTuneConfig(
            evaluation_threshold=0.7,
            max_auto_finetune_epochs=5,
            auto_finetune_learning_rate=1e-4,
            adapter_save_path="/custom/path",
        )
        assert config.evaluation_threshold == 0.7
        assert config.max_auto_finetune_epochs == 5
        assert config.auto_finetune_learning_rate == 1e-4
        assert config.adapter_save_path == "/custom/path"


class TestFineTuneTriggerRecord:
    """Test FineTuneTriggerRecord dataclass"""
    
    def test_default_record(self):
        record = FineTuneTriggerRecord(
            trigger_id="test_123",
            requirement_id="req_456",
            evaluation_score=0.5,
            trigger_timestamp=datetime.now(),
            fine_tune_config=Mock(),
            training_examples_count=3,
        )
        
        assert record.trigger_id == "test_123"
        assert record.requirement_id == "req_456"
        assert record.evaluation_score == 0.5
        assert record.training_examples_count == 3
        assert record.fine_tune_results is None
        assert record.adapter_reloaded is False
        assert record.status == "triggered"


class TestAutoFineTuneTrigger:
    """Test AutoFineTuneTrigger"""
    
    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.load_lora_adapter = Mock()
        return engine
    
    @pytest.fixture
    def mock_pipeline(self):
        pipeline = Mock()
        pipeline.fine_tune = Mock(return_value={
            "final_loss": 0.3,
            "loss_decreased": True,
            "loss_history": [0.5, 0.4, 0.3],
        })
        pipeline.save_adapter = Mock(return_value="/path/to/adapter")
        return pipeline
    
    @pytest.fixture
    def config(self):
        return AutoFineTuneConfig(
            evaluation_threshold=0.8,
            max_auto_finetune_epochs=2,
            auto_finetune_learning_rate=1e-4,
        )
    
    @pytest.fixture
    def trigger(self, mock_engine, mock_pipeline, config):
        return AutoFineTuneTrigger(mock_engine, mock_pipeline, config)
    
    def test_init(self, trigger, mock_engine, mock_pipeline, config):
        assert trigger.engine == mock_engine
        assert trigger.pipeline == mock_pipeline
        assert trigger.config == config
        assert trigger._trigger_history == []
        assert trigger._active_finetunes == 0
    
    def test_check_evaluation_score_below_threshold(self, trigger):
        """Test trigger when score below threshold"""
        eval_result = {"score": 0.6, "passes": False}
        assert trigger.check_evaluation_score(eval_result) is True
    
    def test_check_evaluation_score_above_threshold(self, trigger):
        """Test no trigger when score above threshold"""
        eval_result = {"score": 0.9, "passes": True}
        assert trigger.check_evaluation_score(eval_result) is False
    
    def test_check_evaluation_score_fails_explicitly(self, trigger):
        """Test trigger when passes is False"""
        eval_result = {"score": 0.9, "passes": False}
        assert trigger.check_evaluation_score(eval_result) is True
    
    def test_check_evaluation_score_defaults(self, trigger):
        """Test with default values (should not trigger)"""
        eval_result = {}
        # Default score is 1.0, default passes is True
        assert trigger.check_evaluation_score(eval_result) is False
    
    def test_trigger_fine_tune_basic(self, trigger, mock_pipeline):
        """Test basic fine-tune trigger"""
        record = trigger.trigger_fine_tune(
            requirement_id="req_123",
            eval_result={"score": 0.5, "passes": False},
            failed_requirement="Implement login",
            expected_behavior="User can login",
            actual_output="Login failed",
        )
        
        assert record.requirement_id == "req_123"
        assert record.evaluation_score == 0.5
        assert record.training_examples_count == 1
        assert record.status == "completed"
        assert record.fine_tune_results is not None
        assert record.adapter_reloaded is True
        
        # Verify pipeline was called
        mock_pipeline.fine_tune.assert_called_once()
        mock_pipeline.save_adapter.assert_called_once()
        trigger.engine.load_lora_adapter.assert_called_once()
    
    def test_trigger_fine_tune_max_concurrent(self, trigger):
        """Test that max concurrent fine-tunes is respected"""
        trigger._active_finetunes = trigger.config.max_concurrent_finetunes
        
        record = trigger.trigger_fine_tune(
            requirement_id="req_123",
            eval_result={"score": 0.5, "passes": False},
            failed_requirement="Test",
            expected_behavior="Test",
            actual_output="Test",
        )
        
        assert record.status == "skipped_max_concurrent"
    
    def test_trigger_fine_tune_handles_exception(self, trigger, mock_pipeline):
        """Test that exceptions during fine-tune are handled"""
        mock_pipeline.fine_tune.side_effect = Exception("Training failed")
        
        record = trigger.trigger_fine_tune(
            requirement_id="req_123",
            eval_result={"score": 0.5, "passes": False},
            failed_requirement="Test",
            expected_behavior="Test",
            actual_output="Test",
        )
        
        assert record.status == "failed"
        assert "error" in record.fine_tune_results
    
    def test_reload_adapter(self, trigger):
        """Test adapter reload"""
        trigger.reload_adapter("/path/to/adapter")
        trigger.engine.load_lora_adapter.assert_called_once_with("/path/to/adapter")
    
    def test_get_trigger_history(self, trigger):
        """Test getting trigger history"""
        assert trigger.get_trigger_history() == []
        
        # Add a record
        trigger._trigger_history.append(Mock())
        assert len(trigger.get_trigger_history()) == 1
    
    def test_get_latest_trigger(self, trigger):
        """Test getting latest trigger"""
        assert trigger.get_latest_trigger() is None
        
        mock_record = Mock()
        trigger._trigger_history.append(mock_record)
        assert trigger.get_latest_trigger() == mock_record
    
    def test_get_statistics(self, trigger):
        """Test statistics calculation"""
        stats = trigger.get_statistics()
        
        assert stats["total_triggers"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["active_finetunes"] == 0
    
    def test_get_statistics_with_records(self, trigger):
        """Test statistics with trigger records"""
        # Add mock records with different statuses
        trigger._trigger_history = [
            Mock(status="completed", fine_tune_results={"loss_decreased": True}),
            Mock(status="completed", fine_tune_results={"loss_decreased": False}),
            Mock(status="failed", fine_tune_results={}),
            Mock(status="skipped_max_concurrent", fine_tune_results=None),
        ]
        
        stats = trigger.get_statistics()
        
        assert stats["total_triggers"] == 4
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["skipped"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["loss_decreased_rate"] == 0.5


class TestCreateAutoFineTuneTrigger:
    """Test factory function"""
    
    def test_create_auto_finetune_trigger(self):
        mock_engine = Mock()
        
        trigger = create_auto_finetune_trigger(mock_engine)
        
        assert isinstance(trigger, AutoFineTuneTrigger)
        assert trigger.engine == mock_engine
        assert trigger.pipeline is not None
        assert trigger.config is not None
    
    def test_create_auto_finetune_trigger_with_config(self):
        mock_engine = Mock()
        config = AutoFineTuneConfig(evaluation_threshold=0.7)
        
        trigger = create_auto_finetune_trigger(mock_engine, config)
        
        assert trigger.config.evaluation_threshold == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])