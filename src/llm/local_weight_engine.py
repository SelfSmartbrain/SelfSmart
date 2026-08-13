"""
Direct PyTorch & Hugging Face Weight Engine for native local LLM fine-tuning.

This module loads model weights directly into PyTorch memory using transformers and PEFT,
eliminating external HTTP API calls for inference and fine-tuning.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GenerationConfig,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, PeftModel, TaskType

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelLoadConfig:
    """Configuration for loading a local model"""

    model_name_or_path: str
    device: str = "auto"  # "auto", "mps", "cuda", "cpu"
    torch_dtype: str = "bfloat16"  # "bfloat16", "float16", "float32"
    use_4bit: bool = False
    use_8bit: bool = False
    quantization_config: Optional[BitsAndBytesConfig] = None
    low_cpu_mem_usage: bool = True
    trust_remote_code: bool = True


@dataclass
class LoRAConfig:
    """Configuration for LoRA adapter"""

    r: int = 8
    lora_alpha: int = 16
    target_modules: List[str] = None
    lora_dropout: float = 0.05
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


class LocalWeightEngine:
    """
    Native PyTorch engine for loading local LLM weights and performing direct inference/fine-tuning.

    Supports:
    - Qwen2.5-0.5B, Llama-3.2-1B, Phi-3.5-mini, and other HF models
    - Automatic device selection (MPS for Apple Silicon, CUDA, CPU)
    - 4-bit/8-bit quantization via bitsandbytes
    - LoRA/PEFT adapters for parameter-efficient fine-tuning
    - Direct weight manipulation without external API calls
    """

    def __init__(self):
        self._model: Optional[AutoModelForCausalLM] = None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._generation_config: Optional[GenerationConfig] = None
        self._device: torch.device = None
        self._model_name: str = ""
        self._peft_config: Optional[LoRAConfig] = None
        self._is_peft_model: bool = False

    def _resolve_device(self, device: str) -> torch.device:
        """Resolve device string to torch.device"""
        if device == "auto":
            if torch.backends.mps.is_available():
                return torch.device("mps")
            elif torch.cuda.is_available():
                return torch.device("cuda")
            else:
                return torch.device("cpu")
        return torch.device(device)

    def _resolve_dtype(self, dtype_str: str) -> torch.dtype:
        """Resolve dtype string to torch.dtype"""
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }
        return dtype_map.get(dtype_str, torch.bfloat16)

    def load_model(self, config: ModelLoadConfig) -> None:
        """
        Load model and tokenizer directly into PyTorch memory.

        Args:
            config: ModelLoadConfig with model path and loading options
        """
        self._model_name = config.model_name_or_path
        self._device = self._resolve_device(config.device)
        torch_dtype = self._resolve_dtype(config.torch_dtype)

        logger.info(
            f"Loading model: {config.model_name_or_path} on {self._device} with {config.torch_dtype}"
        )

        # Load tokenizer
        self._tokenizer = AutoTokenizer.from_pretrained(
            config.model_name_or_path,
            trust_remote_code=config.trust_remote_code,
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        # Configure quantization if requested
        quantization_config = config.quantization_config
        if config.use_4bit and quantization_config is None:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch_dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif config.use_8bit and quantization_config is None:
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )

        # Load model
        self._model = AutoModelForCausalLM.from_pretrained(
            config.model_name_or_path,
            torch_dtype=torch_dtype,
            device_map=None if str(self._device) == "cpu" else "auto",
            low_cpu_mem_usage=config.low_cpu_mem_usage,
            quantization_config=quantization_config,
            trust_remote_code=config.trust_remote_code,
        )

        # Move to device if not using device_map
        if str(self._device) == "cpu" or config.device != "auto":
            self._model = self._model.to(self._device)

        # Load generation config
        try:
            self._generation_config = GenerationConfig.from_pretrained(config.model_name_or_path)
        except Exception:
            self._generation_config = GenerationConfig(
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.1,
                pad_token_id=self._tokenizer.pad_token_id,
                eos_token_id=self._tokenizer.eos_token_id,
            )

        self._model.eval()
        logger.info(f"Model loaded successfully on {self._model.device}")

    def attach_lora(self, lora_config: LoRAConfig) -> None:
        """
        Attach LoRA adapter for parameter-efficient fine-tuning.

        Args:
            lora_config: LoRAConfig with adapter parameters
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        self._peft_config = lora_config

        peft_config = LoraConfig(
            r=lora_config.r,
            lora_alpha=lora_config.lora_alpha,
            target_modules=lora_config.target_modules,
            lora_dropout=lora_config.lora_dropout,
            bias=lora_config.bias,
            task_type=TaskType.CAUSAL_LM,
        )

        self._model = get_peft_model(self._model, peft_config)
        self._is_peft_model = True
        self._model.print_trainable_parameters()
        logger.info("LoRA adapter attached successfully")

    def load_lora_adapter(self, adapter_path: str) -> None:
        """
        Load a saved LoRA adapter from disk.

        Args:
            adapter_path: Path to the saved adapter directory or .safetensors file
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        self._model = PeftModel.from_pretrained(self._model, adapter_path)
        self._is_peft_model = True
        logger.info(f"Loaded LoRA adapter from {adapter_path}")

    def save_lora_adapter(self, save_path: str) -> None:
        """
        Save the current LoRA adapter to disk.

        Args:
            save_path: Directory path to save adapter
        """
        if not self._is_peft_model:
            raise RuntimeError("No LoRA adapter attached. Call attach_lora() first.")

        os.makedirs(save_path, exist_ok=True)
        self._model.save_pretrained(save_path)
        self._tokenizer.save_pretrained(save_path)
        logger.info(f"Saved LoRA adapter to {save_path}")

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        repetition_penalty: float = 1.1,
        do_sample: bool = True,
        **kwargs,
    ) -> str:
        """
        Generate text directly from the loaded model.

        Args:
            prompt: Input prompt string
            max_new_tokens: Maximum new tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            repetition_penalty: Repetition penalty
            do_sample: Whether to use sampling

        Returns:
            Generated text string
        """
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Tokenize prompt
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)

        # Prepare generation config
        gen_config = self._generation_config
        gen_config.max_new_tokens = max_new_tokens
        gen_config.temperature = temperature
        gen_config.top_p = top_p
        gen_config.top_k = top_k
        gen_config.repetition_penalty = repetition_penalty
        gen_config.do_sample = do_sample and temperature > 0
        gen_config.pad_token_id = self._tokenizer.pad_token_id
        gen_config.eos_token_id = self._tokenizer.eos_token_id

        # Generate
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                generation_config=gen_config,
            )

        # Decode only new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        generated_text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)

        return generated_text

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if self._model is None:
            return {"status": "not_loaded"}

        total_params = sum(p.numel() for p in self._model.parameters())
        trainable_params = sum(p.numel() for p in self._model.parameters() if p.requires_grad)

        return {
            "model_name": self._model_name,
            "device": str(self._model.device),
            "dtype": str(next(self._model.parameters()).dtype),
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "is_peft_model": self._is_peft_model,
            "peft_config": self._peft_config.__dict__ if self._peft_config else None,
        }

    def enable_training_mode(self) -> None:
        """Enable training mode (for fine-tuning)"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        self._model.train()

    def enable_eval_mode(self) -> None:
        """Enable evaluation mode (for inference)"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        self._model.eval()

    def get_trainable_parameters(self):
        """Get trainable parameters for optimizer"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return [p for p in self._model.parameters() if p.requires_grad]

    def forward(self, input_ids: torch.Tensor, labels: torch.Tensor = None, **kwargs):
        """Direct forward pass for training"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return self._model(input_ids=input_ids, labels=labels, **kwargs)

    @property
    def model(self) -> Optional[AutoModelForCausalLM]:
        return self._model

    @property
    def tokenizer(self) -> Optional[AutoTokenizer]:
        return self._tokenizer

    @property
    def device(self) -> torch.device:
        return self._device

    def unload(self) -> None:
        """Unload model and free memory"""
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        self._model_name = ""
        self._peft_config = None
        self._is_peft_model = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
        logger.info("Model unloaded, memory freed")
