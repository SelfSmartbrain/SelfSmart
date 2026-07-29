"""
LoRA Trainer - Fine-tune models with LoRA adapters
Production-grade LoRA training implementation for LLM fine-tuning.
"""

import torch
from transformers import Trainer, TrainingArguments
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig, get_peft_model
from datasets import Dataset
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class LoRATrainer:
    """
    Production-grade LoRA trainer for LLM fine-tuning.
    Uses SFT (Supervised Fine-Tuning) with LoRA adapters.
    """

    def __init__(
        self, model, tokenizer, output_dir: str = "./model_checkpoints", max_seq_length: int = 512
    ):
        """
        Initialize LoRA trainer.

        Args:
            model: Base model to fine-tune
            tokenizer: Tokenizer for the model
            output_dir: Output directory for checkpoints
            max_seq_length: Maximum sequence length
        """
        self.model = model
        self.tokenizer = tokenizer
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.max_seq_length = max_seq_length
        self.trainer = None
        self.version_metadata = {}

        logger.info(f"LoRA trainer initialized with output directory: {self.output_dir}")

    def get_lora_config(
        self,
        r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05,
        target_modules: Optional[List[str]] = None,
    ) -> LoraConfig:
        """
        Get LoRA configuration.

        Args:
            r: LoRA rank
            lora_alpha: LoRA alpha
            lora_dropout: Dropout rate
            target_modules: Target modules for LoRA

        Returns:
            LoraConfig instance
        """
        # Default target modules
        if target_modules is None:
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

        return LoraConfig(
            r=r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
        )

    def prepare_model(self, lora_config: LoraConfig):
        """
        Prepare model with LoRA adapters.

        Args:
            lora_config: LoRA configuration
        """
        logger.info("Preparing model with LoRA adapters")

        # Apply LoRA
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()

        # Enable gradient checkpointing for memory efficiency
        self.model.gradient_checkpointing_enable()

        logger.info("Model prepared with LoRA adapters")

    def load_training_data(self, data_path: str, format_type: str = "instruction") -> Dataset:
        """
        Load training data from JSON file.

        Args:
            data_path: Path to training data JSON
            format_type: Format type (instruction, completion, conversation)

        Returns:
            Dataset instance
        """
        logger.info(f"Loading training data from {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Format data based on type
        if format_type == "instruction":
            formatted_data = []
            for item in data:
                # Create training text from instruction format
                instruction = item.get("instruction", "")
                input_text = item.get("input", "")
                output_text = item.get("output", "")

                if input_text:
                    training_text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output_text}"
                else:
                    training_text = (
                        f"### Instruction:\n{instruction}\n\n### Response:\n{output_text}"
                    )

                formatted_data.append({"text": training_text})

            dataset = Dataset.from_list(formatted_data)

        elif format_type == "completion":
            dataset = Dataset.from_list(data)

        else:
            raise ValueError(f"Unsupported format type: {format_type}")

        logger.info(f"Loaded {len(dataset)} training samples")
        return dataset

    def get_training_arguments(
        self,
        num_train_epochs: int = 3,
        per_device_train_batch_size: int = 4,
        gradient_accumulation_steps: int = 4,
        learning_rate: float = 2e-4,
        warmup_steps: int = 100,
        logging_steps: int = 10,
        save_steps: int = 500,
        eval_steps: int = 500,
        save_total_limit: int = 3,
    ) -> SFTConfig:
        """
        Get training arguments.

        Args:
            num_train_epochs: Number of training epochs
            per_device_train_batch_size: Batch size per device
            gradient_accumulation_steps: Gradient accumulation steps
            learning_rate: Learning rate
            warmup_steps: Warmup steps
            logging_steps: Logging frequency
            save_steps: Checkpoint save frequency
            eval_steps: Evaluation frequency
            save_total_limit: Max checkpoints to keep

        Returns:
            SFTConfig instance
        """
        return SFTConfig(
            dataset_text_field="text",
            max_length=self.max_seq_length,
            output_dir=str(self.output_dir),
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            save_steps=save_steps,
            eval_steps=eval_steps,
            eval_strategy="steps",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            fp16=True if not torch.backends.mps.is_available() else False,
            bf16=False,
            optim="paged_adamw_32bit" if torch.cuda.is_available() else "adamw_torch",
            report_to=["tensorboard"],
            logging_dir=f"{self.output_dir}/logs",
            save_total_limit=save_total_limit,
            lr_scheduler_type="cosine",
            weight_decay=0.01,
            max_grad_norm=1.0,
            dataloader_num_workers=4,
            remove_unused_columns=False,
        )

    def train(
        self,
        train_data_path: str,
        val_data_path: Optional[str] = None,
        lora_config: Optional[LoraConfig] = None,
        training_args: Optional[TrainingArguments] = None,
        data_hash: Optional[str] = None,
    ):
        """
        Train the model with LoRA.

        Args:
            train_data_path: Path to training data
            val_data_path: Path to validation data (optional)
            lora_config: LoRA configuration (optional)
            training_args: Training arguments (optional)
            data_hash: Hash of training data for versioning (optional)
        """
        logger.info("Starting LoRA training")

        # Generate version ID
        timestamp = datetime.utcnow().isoformat()
        version_id = f"v{timestamp.replace(':', '-').replace('.', '-')}"

        # Create versioned output directory
        version_output_dir = self.output_dir / version_id
        version_output_dir.mkdir(parents=True, exist_ok=True)

        # Save data hash to a file for easy verification
        data_hash_file = version_output_dir / "DATA_HASH.txt"
        with open(data_hash_file, "w") as f:
            f.write(data_hash or "unknown")

        # Store version metadata
        self.version_metadata = {
            "version_id": version_id,
            "timestamp": timestamp,
            "data_hash": data_hash,
            "base_model": getattr(self.model, "name_or_path", "unknown"),
            "lora_config": (
                {
                    "r": lora_config.r if lora_config else 16,
                    "lora_alpha": lora_config.lora_alpha if lora_config else 32,
                    "lora_dropout": lora_config.lora_dropout if lora_config else 0.05,
                }
                if lora_config
                else None
            ),
        }

        # Load training data
        train_dataset = self.load_training_data(train_data_path)
        self.version_metadata["train_samples"] = len(train_dataset)

        # Load validation data if provided
        eval_dataset = None
        if val_data_path:
            eval_dataset = self.load_training_data(val_data_path)
            self.version_metadata["val_samples"] = len(eval_dataset)

        # Get default configs if not provided
        if lora_config is None:
            lora_config = self.get_lora_config()

        if training_args is None:
            training_args = self.get_training_arguments()

        # Update output_dir to versioned directory
        training_args.output_dir = str(version_output_dir)

        # Prepare model
        self.prepare_model(lora_config)

        # Create SFT trainer
        self.trainer = SFTTrainer(
            model=self.model,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            args=training_args,
        )

        # Train
        logger.info("Starting training...")
        self.trainer.train()

        # Save final model
        self.trainer.save_model()
        self.tokenizer.save_pretrained(str(version_output_dir))

        # Evaluate on the validation set if available
        if eval_dataset is not None:
            logger.info("Running final evaluation on validation set...")
            eval_results = self.trainer.evaluate(eval_dataset)
            logger.info(f"Final evaluation results: {eval_results}")
            self.version_metadata["eval_metrics"] = eval_results
        else:
            self.version_metadata["eval_metrics"] = None

        # Save version metadata
        metadata_path = version_output_dir / "version_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.version_metadata, f, indent=2)

        # Create symlink to latest version
        latest_link = self.output_dir / "latest"
        if latest_link.exists():
            latest_link.unlink()
        try:
            latest_link.symlink_to(version_output_dir)
        except OSError:
            # Symlink may not work on all systems, skip
            pass

        logger.info(f"Training complete. Model saved to {version_output_dir}")
        logger.info(f"Version ID: {version_id}")
        logger.info(f"Version metadata saved to {metadata_path}")

        return version_output_dir

    def evaluate_model(self, eval_dataset: Dataset, max_samples: int = 10) -> Dict[str, Any]:
        """
        Basic evaluation gate to detect catastrophic forgetting.
        Evaluates model on a small sample of the evaluation dataset.

        Args:
            eval_dataset: Evaluation dataset
            max_samples: Maximum number of samples to evaluate

        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Running evaluation gate on {min(max_samples, len(eval_dataset))} samples")

        if self.trainer is None:
            logger.warning("No trainer initialized, skipping evaluation")
            return {"status": "skipped", "reason": "no_trainer"}

        try:
            # Run evaluation on a small subset
            eval_results = self.trainer.evaluate(
                eval_dataset=eval_dataset.select(range(min(max_samples, len(eval_dataset))))
            )

            logger.info(f"Evaluation results: {eval_results}")

            return {
                "status": "success",
                "metrics": eval_results,
                "samples_evaluated": min(max_samples, len(eval_dataset)),
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {"status": "error", "error": str(e)}

    def save_model(self, output_dir: Optional[str] = None):
        """
        Save the fine-tuned model.

        Args:
            output_dir: Output directory (optional)
        """
        if output_dir is None:
            output_dir = self.output_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        if self.trainer:
            self.trainer.save_model(str(output_dir))
            self.tokenizer.save_pretrained(str(output_dir))
            logger.info(f"Model saved to {output_dir}")
        else:
            logger.warning("No trainer to save")

    def load_model(self, checkpoint_path: str):
        """
        Load a fine-tuned model from checkpoint.

        Args:
            checkpoint_path: Path to checkpoint directory
        """
        from peft import PeftModel

        logger.info(f"Loading fine-tuned model from {checkpoint_path}")

        # Load LoRA adapters
        self.model = PeftModel.from_pretrained(self.model, checkpoint_path)

        # Load tokenizer
        self.tokenizer = self.tokenizer.from_pretrained(checkpoint_path)

        logger.info("Fine-tuned model loaded successfully")

    def get_training_stats(self) -> Dict[str, Any]:
        """
        Get training statistics.

        Returns:
            Dictionary of training statistics
        """
        if self.trainer is None:
            return {}

        state = self.trainer.state
        return {
            "global_step": state.global_step,
            "epoch": state.epoch,
            "max_steps": state.max_steps,
            "log_history": state.log_history[-10:],  # Last 10 logs
        }
