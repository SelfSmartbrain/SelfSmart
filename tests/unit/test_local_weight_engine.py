"""
Unit tests for LocalWeightEngine - Direct PyTorch & Hugging Face Weight Engine
"""

import pytest
import torch
from unittest.mock import Mock, patch, MagicMock

# Import the module under test
from src.llm.local_weight_engine import (
    LocalWeightEngine,
    ModelLoadConfig,
    LoRAConfig,
)


class TestLocalWeightEngine:
    """Test cases for LocalWeightEngine"""
    
    def test_device_resolution(self):
        """Test device resolution logic"""
        engine = LocalWeightEngine()
        
        # Test auto device - should pick available device
        device = engine._resolve_device("auto")
        assert isinstance(device, torch.device)
        assert device.type in ["mps", "cuda", "cpu"]
        
        # Test explicit device selection
        assert engine._resolve_device("cpu").type == "cpu"
        assert engine._resolve_device("mps").type == "mps"
        assert engine._resolve_device("cuda").type == "cuda"
    
    def test_dtype_resolution(self):
        """Test dtype resolution logic"""
        engine = LocalWeightEngine()
        
        assert engine._resolve_dtype("bfloat16") == torch.bfloat16
        assert engine._resolve_dtype("float16") == torch.float16
        assert engine._resolve_dtype("float32") == torch.float32
        # Default fallback
        assert engine._resolve_dtype("unknown") == torch.bfloat16
    
    def test_model_load_config_creation(self):
        """Test ModelLoadConfig dataclass creation"""
        config = ModelLoadConfig(
            model_name_or_path="test-model",
            device="cpu",
            torch_dtype="float32",
            use_4bit=False,
            use_8bit=False,
        )
        
        assert config.model_name_or_path == "test-model"
        assert config.device == "cpu"
        assert config.torch_dtype == "float32"
        assert config.use_4bit is False
        assert config.use_8bit is False
    
    def test_lora_config_creation(self):
        """Test LoRAConfig dataclass creation"""
        config = LoRAConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.1,
        )
        
        assert config.r == 16
        assert config.lora_alpha == 32
        assert config.target_modules == ["q_proj", "v_proj"]
        assert config.lora_dropout == 0.1
        assert config.bias == "none"
        assert config.task_type == "CAUSAL_LM"
    
    def test_lora_config_defaults(self):
        """Test LoRAConfig default values"""
        config = LoRAConfig()
        
        assert config.r == 8
        assert config.lora_alpha == 16
        assert config.target_modules == ["q_proj", "v_proj", "k_proj", "o_proj"]
        assert config.lora_dropout == 0.05
    
    @patch('src.llm.local_weight_engine.AutoModelForCausalLM.from_pretrained')
    @patch('src.llm.local_weight_engine.AutoTokenizer.from_pretrained')
    @patch('src.llm.local_weight_engine.GenerationConfig.from_pretrained')
    def test_load_model_success(self, mock_gen_config, mock_tokenizer, mock_model):
        """Test successful model loading"""
        # Setup mocks
        mock_model_instance = Mock()
        mock_model_instance.parameters.return_value = [torch.nn.Parameter(torch.randn(10, 10))]
        mock_model_instance.to.return_value = mock_model_instance
        mock_model_instance.eval.return_value = None
        mock_model_instance.device = torch.device("cpu")
        mock_model.return_value = mock_model_instance
        
        mock_tokenizer_instance = Mock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.eos_token = "<eos>"
        mock_tokenizer.return_value = mock_tokenizer_instance
        
        mock_gen_config_instance = Mock()
        mock_gen_config.return_value = mock_gen_config_instance
        
        # Create engine and load
        engine = LocalWeightEngine()
        config = ModelLoadConfig(
            model_name_or_path="test-model",
            device="cpu",
            torch_dtype="float32",
        )
        
        engine.load_model(config)
        
        # Verify
        assert engine._model is not None
        assert engine._tokenizer is not None
        assert engine._generation_config is not None
        assert engine._model_name == "test-model"
        mock_model.assert_called_once()
        mock_tokenizer.assert_called_once()
    
    @patch('src.llm.local_weight_engine.get_peft_model')
    @patch('src.llm.local_weight_engine.LoraConfig')
    def test_attach_lora(self, mock_lora_config_class, mock_get_peft_model):
        """Test LoRA adapter attachment"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        engine._model.print_trainable_parameters = Mock()
        
        mock_peft_model = Mock()
        mock_get_peft_model.return_value = mock_peft_model
        
        lora_config = LoRAConfig(r=8, lora_alpha=16)
        engine.attach_lora(lora_config)
        
        # Verify
        assert engine._is_peft_model is True
        assert engine._peft_config is not None
        mock_lora_config_class.assert_called_once()
        mock_get_peft_model.assert_called_once()
        engine._model.print_trainable_parameters.assert_called_once()
    
    def test_attach_lora_without_model_raises(self):
        """Test attaching LoRA without model raises error"""
        engine = LocalWeightEngine()
        engine._model = None
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            engine.attach_lora(LoRAConfig())
    
    def test_generate_without_model_raises(self):
        """Test generation without model raises error"""
        engine = LocalWeightEngine()
        engine._model = None
        engine._tokenizer = None
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            engine.generate("test prompt")
    
    @patch('src.llm.local_weight_engine.PeftModel.from_pretrained')
    def test_load_lora_adapter(self, mock_from_pretrained):
        """Test loading saved LoRA adapter"""
        engine = LocalWeightEngine()
        mock_model = Mock()
        engine._model = mock_model
        
        mock_peft_model = Mock()
        mock_from_pretrained.return_value = mock_peft_model
        
        engine.load_lora_adapter("/path/to/adapter")
        
        assert engine._is_peft_model is True
        mock_from_pretrained.assert_called_once_with(mock_model, "/path/to/adapter")
    
    def test_save_lora_adapter_without_peft_raises(self):
        """Test saving adapter without PEFT raises error"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        engine._is_peft_model = False
        
        with pytest.raises(RuntimeError, match="No LoRA adapter attached"):
            engine.save_lora_adapter("/path/to/save")
    
    @patch('src.llm.local_weight_engine.os.makedirs')
    def test_save_lora_adapter(self, mock_makedirs):
        """Test saving LoRA adapter"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        engine._tokenizer = Mock()
        engine._is_peft_model = True
        
        engine.save_lora_adapter("/path/to/save")
        
        mock_makedirs.assert_called_once_with("/path/to/save", exist_ok=True)
        engine._model.save_pretrained.assert_called_once_with("/path/to/save")
        engine._tokenizer.save_pretrained.assert_called_once_with("/path/to/save")
    
    def test_get_model_info_not_loaded(self):
        """Test get_model_info when model not loaded"""
        engine = LocalWeightEngine()
        info = engine.get_model_info()
        
        assert info == {"status": "not_loaded"}
    
    def test_get_model_info_loaded(self):
        """Test get_model_info when model loaded"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        # Mock parameters() to return a fresh iterator each time
        mock_param = Mock()
        mock_param.numel.return_value = 100
        mock_param.requires_grad = True
        mock_param.dtype = torch.float32
        
        def params_iterator():
            return iter([mock_param])
        
        engine._model.parameters.side_effect = params_iterator
        engine._model.device = torch.device("cpu")
        engine._model_name = "test-model"
        engine._is_peft_model = False
        
        info = engine.get_model_info()
        
        assert info["model_name"] == "test-model"
        assert info["device"] == "cpu"
        assert info["is_peft_model"] is False
        assert info["total_parameters"] == 100
        assert info["trainable_parameters"] == 100
    
    def test_enable_training_mode(self):
        """Test enabling training mode"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        
        engine.enable_training_mode()
        
        engine._model.train.assert_called_once()
    
    def test_enable_eval_mode(self):
        """Test enabling eval mode"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        
        engine.enable_eval_mode()
        
        engine._model.eval.assert_called_once()
    
    def test_get_trainable_parameters(self):
        """Test getting trainable parameters"""
        engine = LocalWeightEngine()
        param1 = Mock()
        param1.requires_grad = True
        param2 = Mock()
        param2.requires_grad = False
        param3 = Mock()
        param3.requires_grad = True
        
        engine._model = Mock()
        engine._model.parameters.return_value = [param1, param2, param3]
        
        trainable = engine.get_trainable_parameters()
        
        assert len(trainable) == 2
        assert param1 in trainable
        assert param3 in trainable
        assert param2 not in trainable
    
    def test_forward(self):
        """Test direct forward pass"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        mock_output = Mock()
        engine._model.return_value = mock_output
        
        input_ids = torch.tensor([[1, 2, 3]])
        labels = torch.tensor([[1, 2, 3]])
        
        result = engine.forward(input_ids, labels=labels)
        
        assert result == mock_output
        engine._model.assert_called_once_with(input_ids=input_ids, labels=labels)
    
    def test_unload(self):
        """Test model unloading"""
        engine = LocalWeightEngine()
        engine._model = Mock()
        engine._tokenizer = Mock()
        engine._model_name = "test-model"
        
        with patch('torch.cuda.empty_cache') as mock_cuda_cache:
            with patch('torch.backends.mps.is_available', return_value=False):
                engine.unload()
        
        assert engine._model is None
        assert engine._tokenizer is None
        assert engine._model_name == ""
    
    def test_model_property(self):
        """Test model property accessor"""
        engine = LocalWeightEngine()
        assert engine.model is None
        
        mock_model = Mock()
        engine._model = mock_model
        assert engine.model == mock_model
    
    def test_tokenizer_property(self):
        """Test tokenizer property accessor"""
        engine = LocalWeightEngine()
        assert engine.tokenizer is None
        
        mock_tokenizer = Mock()
        engine._tokenizer = mock_tokenizer
        assert engine.tokenizer == mock_tokenizer
    
    def test_device_property(self):
        """Test device property accessor"""
        engine = LocalWeightEngine()
        assert engine.device is None
        
        device = torch.device("cpu")
        engine._device = device
        assert engine.device == device


if __name__ == "__main__":
    pytest.main([__file__, "-v"])