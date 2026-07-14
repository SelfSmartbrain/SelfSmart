"""
Training Script - Fine-tune custom LLM
Run with: python train_model.py
"""

import asyncio
import logging
import random
import numpy as np
import torch
import json
import hashlib
from pathlib import Path
from datetime import datetime

from src.llm_training.data_collector import DataCollector
from src.llm_training.data_preprocessor import DataPreprocessor
from src.llm_training.model_loader import ModelLoader
from src.llm_training.lora_trainer import LoRATrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set global random seeds for reproducibility
def set_seed(seed: int = 42):
    """Set random seeds for Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # Ensure deterministic behavior (may impact performance)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    logger.info(f"Random seed set to {seed}")

def compute_data_hash(data: list) -> str:
    """Compute SHA256 hash of training data for versioning."""
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()[:16]

async def main():
    """Main training pipeline optimized for M1 Mac."""

    # Set random seed for reproducibility
    set_seed(seed=42)

    # 1. Collect training data
    logger.info("Step 1: Collecting training data from internet...")
    async with DataCollector() as collector:
        data = await collector.collect_all(
            wikipedia_count=50,  # Reduced for faster training
            hacker_news_count=50
        )

    # 2. Preprocess data
    logger.info("Step 2: Preprocessing data...")
    preprocessor = DataPreprocessor()
    processed_data = preprocessor.process_all(format_type="instruction")
    preprocessor.create_train_val_split("processed_combined_training_data.json")

    # Compute and save data hash for versioning
    data_hash = compute_data_hash(processed_data)
    metadata = {
        "data_hash": data_hash,
        "timestamp": datetime.utcnow().isoformat(),
        "total_samples": len(processed_data),
        "sources": ["wikipedia", "hacker_news"]
    }
    processed_dir = Path("./training_data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = processed_dir / "dataset_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Data hash: {data_hash} - saved to {metadata_path}")

    # 3. Load model (Phi-3 Mini for M1 Mac)
    logger.info("Step 3: Loading base model (Phi-3 Mini for M1 Mac)...")
    model_loader = ModelLoader(
        model_key="phi-3-mini",
        use_quantization=False  # Quantization not supported on MPS
    )
    model = model_loader.load_model()
    tokenizer = model_loader.load_tokenizer()

    # 4. Fine-tune with LoRA (MPS-optimized)
    logger.info("Step 4: Fine-tuning model with LoRA on MPS...")
    trainer = LoRATrainer(
        model,
        tokenizer,
        output_dir="./model_checkpoints",
        max_seq_length=512  # Reduced for M1 Mac
    )

    # Get training arguments optimized for M1 Mac
    from transformers import TrainingArguments
    training_args = TrainingArguments(
        output_dir="./model_checkpoints",
        num_train_epochs=2,  # Reduced for faster training
        per_device_train_batch_size=2,  # Smaller batch for M1
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        warmup_steps=50,
        logging_steps=10,
        save_steps=100,
        eval_steps=100,
        evaluation_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=False,  # MPS uses bfloat16
        bf16=True,  # Use bfloat16 for MPS
        optim="adamw_torch",
        report_to=["tensorboard"],
        logging_dir="./model_checkpoints/logs",
        save_total_limit=2,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        max_grad_norm=1.0,
        dataloader_num_workers=2,
        remove_unused_columns=False
    )

    trainer.train(
        train_data_path="./training_data/processed/train_processed_combined_training_data.json",
        val_data_path="./training_data/processed/val_processed_combined_training_data.json",
        training_args=training_args,
        num_train_epochs=2,
        data_hash=data_hash
    )

    logger.info("Training complete! Model saved to ./model_checkpoints")
    logger.info("Estimated training time on M1 Mac: 3-6 hours")

if __name__ == "__main__":
    asyncio.run(main())
