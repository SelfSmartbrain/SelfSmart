"""
Unit tests for RequirementFineTunePipeline - Direct Parameter Fine-Tuning Pipeline
"""

import pytest
import torch
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.learning.requirement_finetune_pipeline import (
    RequirementFineTunePipeline,
    FineTuneConfig,
    TrainingExample,
    RequirementDataset,
    create_training_examples_from_feedback,
    create_training_examples_from_code_fix,
)


class TestFineTuneConfig:
    """Test FineTuneConfig dataclass"""
    
    def test_default_config(self):
        config = FineTuneConfig()
        assert config.epochs == 3
        assert config.learning_rate == 2e-4
        assert config.batch_size == 1
        assert config.gradient_accumulation_steps == 4
        assert config.max_grad_norm == 1.0
        assert config.output_dir == "data/adapters/requirement_adapter"
    
    def test_custom_config(self):
        config = FineTuneConfig(
            epochs=5,
            learning_rate=1e-4,
            batch_size=2,
            output_dir="/custom/path",
        )
        assert config.epochs == 5
        assert config.learning_rate == 1e-4
        assert config.batch_size == 2
        assert config.output_dir == "/custom/path"


class TestTrainingExample:
    """Test TrainingExample dataclass"""
    
    def test_creation(self):
        example = TrainingExample(
            prompt="Test prompt",
            completion="Test completion",
            requirement_id="req-123",
        )
        assert example.prompt == "Test prompt"
        assert example.completion == "Test completion"
        assert example.requirement_id == "req-123"
        assert example.metadata == {}
    
    def test_with_metadata(self):
        example = TrainingExample(
            prompt="Test",
            completion="Test",
            requirement_id="req-1",
            metadata={"key": "value"},
        )
        assert example.metadata == {"key": "value"}


class TestRequirementDataset:
    """Test RequirementDataset"""
    
    @pytest.fixture
    def mock_tokenizer(self):
        tokenizer = Mock()
        tokenizer.pad_token = "<pad>"
        tokenizer.eos_token = "<eos>"
        
        # Mock tokenization output
        tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3, 4, 5]]),
            "attention_mask": torch.tensor([[1, 1, 1, 1, 1]]),
        }
        
        # Mock prompt tokenization
        def tokenize_side_effect(text, **kwargs):
            if "padding" in kwargs and not kwargs["padding"]:
                return {"input_ids": torch.tensor([[1, 2]])}
            return {
                "input_ids": torch.tensor([[1, 2, 3, 4, 5]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1]]),
            }
        
        tokenizer.side_effect = tokenize_side_effect
        return tokenizer
    
    @pytest.fixture
    def training_examples(self):
        return [
            TrainingExample(
                prompt="Prompt 1",
                completion="Completion 1",
                requirement_id="req-1",
            ),
            TrainingExample(
                prompt="Prompt 2",
                completion="Completion 2",
                requirement_id="req-2",
            ),
        ]
    
    def test_dataset_length(self, mock_tokenizer, training_examples):
        dataset = RequirementDataset(training_examples, mock_tokenizer, max_seq_length=512)
        assert len(dataset) == 2
    
    def test_dataset_getitem(self, mock_tokenizer, training_examples):
        dataset = RequirementDataset(training_examples, mock_tokenizer, max_seq_length=512)
        item = dataset[0]
        
        assert "input_ids" in item
        assert "attention_mask" in item
        assert "labels" in item
        assert isinstance(item["input_ids"], torch.Tensor)
        assert isinstance(item["attention_mask"], torch.Tensor)
        assert isinstance(item["labels"], torch.Tensor)
    
    def test_labels_mask_prompt(self, mock_tokenizer, training_examples):
        """Test that prompt tokens are masked in labels (-100)"""
        dataset = RequirementDataset(training_examples, mock_tokenizer, max_seq_length=512)
        item = dataset[0]
        
        # First 2 tokens should be -100 (prompt length)
        assert item["labels"][0] == -100
        assert item["labels"][1] == -100
        # Rest should be actual token IDs
        assert item["labels"][2] != -100


class TestRequirementFineTunePipeline:
    """Test RequirementFineTunePipeline"""
    
    @pytest.fixture
    def mock_engine(self):
        engine = Mock(spec=[
            'model', 'tokenizer', 'device', 'get_trainable_parameters',
            'enable_training_mode', 'enable_eval_mode', 'forward',
            'save_lora_adapter', 'load_lora_adapter', '_is_peft_model'
        ])
        engine.model = Mock()
        engine.tokenizer = Mock()
        engine.tokenizer.pad_token = "<pad>"
        engine.tokenizer.eos_token = "<eos>"
        engine.device = torch.device("cpu")
        engine._is_peft_model = True
        
        # Mock trainable parameters - use real tensors with requires_grad
        param1 = torch.nn.Parameter(torch.randn(10, 10))
        param2 = torch.nn.Parameter(torch.randn(10, 10))
        engine.get_trainable_parameters.return_value = [param1, param2]
        
        # Mock forward pass
        mock_output = Mock()
        mock_output.loss = torch.tensor(0.5, requires_grad=True)
        engine.forward.return_value = mock_output
        
        # Mock tokenizer to return proper tensors
        def tokenizer_side_effect(text, **kwargs):
            if "padding" in kwargs and not kwargs["padding"]:
                return {"input_ids": torch.tensor([[1, 2]])}
            return {
                "input_ids": torch.tensor([[1, 2, 3, 4, 5]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1]]),
            }
        
        engine.tokenizer.side_effect = tokenizer_side_effect
        
        return engine
    
    @pytest.fixture
    def config(self):
        return FineTuneConfig(
            epochs=2,
            batch_size=1,
            gradient_accumulation_steps=1,
            logging_steps=10,
        )
    
    @pytest.fixture
    def training_examples(self):
        return [
            TrainingExample(
                prompt="Test prompt",
                completion="Test completion",
                requirement_id="req-1",
            ),
        ]
    
    def test_init(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        assert pipeline.engine == mock_engine
        assert pipeline.config == config
        assert pipeline._optimizer is None
        assert pipeline._global_step == 0
    
    def test_prepare_dataset(self, mock_engine, config, training_examples):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        dataloader = pipeline.prepare_dataset(training_examples)
        
        assert isinstance(dataloader, torch.utils.data.DataLoader)
        assert dataloader.batch_size == 1
    
    def test_prepare_dataset_without_tokenizer_raises(self, config):
        engine = Mock()
        engine.tokenizer = None
        pipeline = RequirementFineTunePipeline(engine, config)
        
        with pytest.raises(RuntimeError, match="Tokenizer not available"):
            pipeline.prepare_dataset([])
    
    def test_setup_optimizer(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        pipeline.setup_optimizer()
        
        assert pipeline._optimizer is not None
        assert isinstance(pipeline._optimizer, torch.optim.AdamW)
    
    def test_setup_optimizer_no_trainable_params_raises(self, config):
        engine = Mock()
        engine.get_trainable_parameters.return_value = []
        engine._is_peft_model = True
        pipeline = RequirementFineTunePipeline(engine, config)
        
        with pytest.raises(RuntimeError, match="No trainable parameters"):
            pipeline.setup_optimizer()
    
    @patch('src.learning.requirement_finetune_pipeline.clip_grad_norm_')
    def test_fine_tune_basic(self, mock_clip_grad, mock_engine, config, training_examples):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        
        results = pipeline.fine_tune(training_examples, epochs=1)
        
        assert results["epochs_completed"] == 1
        assert "final_loss" in results
        assert "loss_history" in results
        assert "loss_decreased" in results
        assert isinstance(results["loss_history"], list)
        
        # Verify training mode was enabled/disabled
        mock_engine.enable_training_mode.assert_called_once()
        mock_engine.enable_eval_mode.assert_called_once()
        
        # Verify optimizer steps
        assert mock_engine.forward.called
        assert mock_clip_grad.called
    
    def test_fine_tune_without_model_raises(self, config, training_examples):
        engine = Mock()
        engine.model = None
        engine._is_peft_model = True
        pipeline = RequirementFineTunePipeline(engine, config)
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            pipeline.fine_tune(training_examples)
    
    def test_fine_tune_without_peft_raises(self, config, training_examples):
        engine = Mock()
        engine.model = Mock()
        engine._is_peft_model = False
        pipeline = RequirementFineTunePipeline(engine, config)
        
        with pytest.raises(RuntimeError, match="LoRA adapter not attached"):
            pipeline.fine_tune(training_examples)
    
    def test_save_adapter(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        path = pipeline.save_adapter("/custom/path")
        
        assert path == "/custom/path"
        mock_engine.save_lora_adapter.assert_called_once_with("/custom/path")
    
    def test_save_adapter_default_path(self, mock_engine):
        config = FineTuneConfig(output_dir="/default/path")
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        path = pipeline.save_adapter()
        
        assert path == "/default/path"
        mock_engine.save_lora_adapter.assert_called_once_with("/default/path")
    
    def test_load_adapter(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        pipeline.load_adapter("/path/to/adapter")
        
        mock_engine.load_lora_adapter.assert_called_once_with("/path/to/adapter")
    
    def test_check_loss_decrease(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        pipeline._training_losses = [1.0, 0.8, 0.6, 0.5]
        
        assert pipeline._check_loss_decrease() is True
    
    def test_check_loss_increase(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        pipeline._training_losses = [0.5, 0.6, 0.7, 0.8]
        
        assert pipeline._check_loss_decrease() is False
    
    def test_check_loss_insufficient_data(self, mock_engine, config):
        pipeline = RequirementFineTunePipeline(mock_engine, config)
        pipeline._training_losses = [0.5]
        
        assert pipeline._check_loss_decrease() is False
        
        pipeline._training_losses = []
        assert pipeline._check_loss_decrease() is False


class TestCreateTrainingExamples:
    """Test training example creation functions"""
    
    def test_create_from_feedback(self):
        examples = create_training_examples_from_feedback(
            failed_requirement="Implement login",
            expected_behavior="User can login with email/password",
            actual_output="Login failed",
            requirement_id="req-123",
        )
        
        assert len(examples) == 1
        example = examples[0]
        assert "Implement login" in example.prompt
        assert "User can login" in example.completion
        assert example.requirement_id == "req-123"
        assert "failed_requirement" in example.metadata
        assert "actual_output" in example.metadata
    
    def test_create_from_code_fix(self):
        examples = create_training_examples_from_code_fix(
            original_code="def add(a, b):\n    return a - b",
            fixed_code="def add(a, b):\n    return a + b",
            issue_description="Add function subtracts instead of adds",
            requirement_id="req-456",
        )
        
        assert len(examples) == 1
        example = examples[0]
        assert "Add function subtracts" in example.prompt
        assert "a + b" in example.completion
        assert example.requirement_id == "req-456"
        assert "issue" in example.metadata
        assert "original_code" in example.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])