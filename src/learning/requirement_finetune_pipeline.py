"""
Direct Parameter Fine-Tuning Pipeline for native local LLM weight updates.

This module implements gradient-based fine-tuning directly on model weights
using PyTorch backpropagation, enabling the system to learn from failed
requirements by updating its own parameters.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Iterator
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from torch.nn.utils import clip_grad_norm_
from transformers import AutoTokenizer
from peft import PeftModel

from src.llm.local_weight_engine import LocalWeightEngine, LoRAConfig
from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FineTuneConfig:
    """Configuration for fine-tuning process"""
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 1
    gradient_accumulation_steps: int = 4
    max_grad_norm: float = 1.0
    warmup_steps: int = 10
    weight_decay: float = 0.01
    max_seq_length: int = 512
    save_steps: int = 50
    logging_steps: int = 10
    output_dir: str = "data/adapters/requirement_adapter"


@dataclass
class TrainingExample:
    """Single training example for requirement fine-tuning"""
    prompt: str
    completion: str
    requirement_id: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RequirementDataset(Dataset):
    """
    Dataset for requirement-based fine-tuning.
    
    Tokenizes prompt-completion pairs from failed requirements
    into input_ids, attention_mask, and labels for causal LM training.
    """
    
    def __init__(
        self,
        examples: List[TrainingExample],
        tokenizer: AutoTokenizer,
        max_seq_length: int = 512,
    ):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def __len__(self) -> int:
        return len(self.examples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        example = self.examples[idx]
        
        # Format as prompt + completion
        full_text = example.prompt + example.completion
        
        # Tokenize full text
        tokenized = self.tokenizer(
            full_text,
            truncation=True,
            max_length=self.max_seq_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        input_ids = tokenized["input_ids"].squeeze(0)
        attention_mask = tokenized["attention_mask"].squeeze(0)
        
        # For causal LM, labels are the same as input_ids
        # We'll mask the prompt portion in the loss calculation
        labels = input_ids.clone()
        
        # Tokenize prompt separately to find its length
        prompt_tokens = self.tokenizer(
            example.prompt,
            truncation=True,
            max_length=self.max_seq_length,
            padding=False,
            return_tensors="pt",
        )
        prompt_length = prompt_tokens["input_ids"].shape[1]
        
        # Mask prompt tokens in labels (set to -100 to ignore in loss)
        labels[:prompt_length] = -100
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


class RequirementFineTunePipeline:
    """
    Fine-tuning pipeline for updating model weights based on requirement feedback.
    
    Implements the complete training loop:
    - Dataset preparation from failed requirements
    - Gradient computation and backpropagation
    - Optimizer steps with gradient clipping
    - Adapter checkpointing to .safetensors
    """
    
    def __init__(
        self,
        engine: LocalWeightEngine,
        config: Optional[FineTuneConfig] = None,
    ):
        self.engine = engine
        self.config = config or FineTuneConfig()
        self._optimizer: Optional[AdamW] = None
        self._scheduler = None
        self._global_step = 0
        self._training_losses: List[float] = []
        
    def prepare_dataset(
        self,
        training_examples: List[TrainingExample],
    ) -> DataLoader:
        """
        Prepare DataLoader from training examples.
        
        Args:
            training_examples: List of TrainingExample objects
            
        Returns:
            DataLoader for training
        """
        if self.engine.tokenizer is None:
            raise RuntimeError("Tokenizer not available. Load model first.")
        
        dataset = RequirementDataset(
            examples=training_examples,
            tokenizer=self.engine.tokenizer,
            max_seq_length=self.config.max_seq_length,
        )
        
        dataloader = DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            drop_last=False,
        )
        
        logger.info(f"Prepared dataset with {len(dataset)} examples")
        return dataloader
    
    def setup_optimizer(self) -> None:
        """Setup optimizer for trainable parameters"""
        trainable_params = self.engine.get_trainable_parameters()
        
        if not trainable_params:
            raise RuntimeError("No trainable parameters found. Attach LoRA adapter first.")
        
        self._optimizer = AdamW(
            trainable_params,
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            betas=(0.9, 0.999),
            eps=1e-8,
        )
        
        logger.info(f"Optimizer initialized with {len(trainable_params)} parameter groups")
    
    def fine_tune(
        self,
        training_examples: List[TrainingExample],
        epochs: Optional[int] = None,
        learning_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute fine-tuning loop with backpropagation.
        
        Args:
            training_examples: List of TrainingExample objects from failed requirements
            epochs: Number of training epochs (overrides config)
            learning_rate: Learning rate (overrides config)
            
        Returns:
            Dictionary with training metrics and results
        """
        if self.engine.model is None:
            raise RuntimeError("Model not loaded. Call engine.load_model() first.")
        
        if not self.engine._is_peft_model:
            raise RuntimeError("LoRA adapter not attached. Call engine.attach_lora() first.")
        
        # Override config if provided
        epochs = epochs or self.config.epochs
        if learning_rate:
            self.config.learning_rate = learning_rate
        
        # Enable training mode
        self.engine.enable_training_mode()
        
        # Setup optimizer
        self.setup_optimizer()
        
        # Prepare dataset
        dataloader = self.prepare_dataset(training_examples)
        
        # Training loop
        total_steps = len(dataloader) * epochs
        logger.info(f"Starting fine-tuning: {epochs} epochs, {total_steps} total steps")
        
        self._training_losses = []
        self._global_step = 0
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            for step, batch in enumerate(dataloader):
                # Move batch to device
                batch = {k: v.to(self.engine.device) for k, v in batch.items()}
                
                # Forward pass
                outputs = self.engine.forward(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    labels=batch["labels"],
                )
                
                loss = outputs.loss
                
                # Scale loss for gradient accumulation
                loss = loss / self.config.gradient_accumulation_steps
                
                # Backward pass
                loss.backward()
                
                epoch_loss += loss.item() * self.config.gradient_accumulation_steps
                num_batches += 1
                
                # Gradient accumulation step
                if (step + 1) % self.config.gradient_accumulation_steps == 0:
                    # Clip gradients
                    clip_grad_norm_(
                        self.engine.get_trainable_parameters(),
                        self.config.max_grad_norm,
                    )
                    
                    # Optimizer step
                    self._optimizer.step()
                    self._optimizer.zero_grad()
                    
                    self._global_step += 1
                    
                    # Logging
                    if self._global_step % self.config.logging_steps == 0:
                        avg_loss = epoch_loss / num_batches if num_batches > 0 else 0
                        logger.info(
                            f"Step {self._global_step}/{total_steps} | "
                            f"Epoch {epoch + 1}/{epochs} | "
                            f"Loss: {avg_loss:.4f}"
                        )
            
            # Log epoch summary
            avg_epoch_loss = epoch_loss / num_batches if num_batches > 0 else 0
            self._training_losses.append(avg_epoch_loss)
            logger.info(f"Epoch {epoch + 1}/{epochs} completed | Avg Loss: {avg_epoch_loss:.4f}")
        
        # Final optimizer step if gradients remain
        if self._optimizer is not None:
            clip_grad_norm_(
                self.engine.get_trainable_parameters(),
                self.config.max_grad_norm,
            )
            self._optimizer.step()
            self._optimizer.zero_grad()
        
        # Return to eval mode
        self.engine.enable_eval_mode()
        
        # Training results
        results = {
            "epochs_completed": epochs,
            "total_steps": self._global_step,
            "final_loss": self._training_losses[-1] if self._training_losses else 0.0,
            "loss_history": self._training_losses,
            "loss_decreased": self._check_loss_decrease(),
        }
        
        logger.info(f"Fine-tuning completed. Final loss: {results['final_loss']:.4f}")
        return results
    
    def _check_loss_decrease(self) -> bool:
        """Check if loss decreased during training"""
        if len(self._training_losses) < 2:
            return False
        return self._training_losses[-1] < self._training_losses[0]
    
    def save_adapter(self, save_path: Optional[str] = None) -> str:
        """
        Save fine-tuned LoRA adapter to disk.
        
        Args:
            save_path: Path to save adapter (uses config default if None)
            
        Returns:
            Path where adapter was saved
        """
        path = save_path or self.config.output_dir
        self.engine.save_lora_adapter(path)
        return path
    
    def load_adapter(self, adapter_path: str) -> None:
        """
        Load a saved LoRA adapter into the engine.
        
        Args:
            adapter_path: Path to the saved adapter
        """
        self.engine.load_lora_adapter(adapter_path)
        logger.info(f"Loaded adapter from {adapter_path}")
    
    @property
    def training_losses(self) -> List[float]:
        return self._training_losses
    
    @property
    def global_step(self) -> int:
        return self._global_step


def create_training_examples_from_feedback(
    failed_requirement: str,
    expected_behavior: str,
    actual_output: str,
    requirement_id: str,
) -> List[TrainingExample]:
    """
    Create training examples from requirement evaluation feedback.
    
    Args:
        failed_requirement: The original requirement that failed
        expected_behavior: What the correct behavior should be
        actual_output: What the model actually produced
        requirement_id: Unique identifier for the requirement
        
    Returns:
        List of TrainingExample objects
    """
    # Create a prompt that includes the requirement and context
    prompt = f"""Requirement: {failed_requirement}

Expected behavior: {expected_behavior}

The following output was incorrect:
{actual_output}

Please provide the correct implementation:"""
    
    # The completion is the expected correct behavior
    completion = f"\n{expected_behavior}"
    
    example = TrainingExample(
        prompt=prompt,
        completion=completion,
        requirement_id=requirement_id,
        metadata={
            "failed_requirement": failed_requirement,
            "actual_output": actual_output,
        }
    )
    
    return [example]


def create_training_examples_from_code_fix(
    original_code: str,
    fixed_code: str,
    issue_description: str,
    requirement_id: str,
) -> List[TrainingExample]:
    """
    Create training examples from a code fix scenario.
    
    Args:
        original_code: The buggy code
        fixed_code: The corrected code
        issue_description: Description of the issue
        requirement_id: Unique identifier for the requirement
        
    Returns:
        List of TrainingExample objects
    """
    prompt = f"""Issue: {issue_description}

Buggy code:
```python
{original_code}
```

Fixed code:"""
    
    completion = f"\n```python\n{fixed_code}\n```"
    
    example = TrainingExample(
        prompt=prompt,
        completion=completion,
        requirement_id=requirement_id,
        metadata={
            "issue": issue_description,
            "original_code": original_code,
        }
    )
    
    return [example]