import os
import sys
import logging
import random
import numpy as np
import torch
import json
from pathlib import Path

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

def main():
    logger.info("Initializing Local Fine-Tuning Pipeline...")

    # Set random seed for reproducibility
    set_seed(seed=42)

    # Check data version for reproducibility
    metadata_path = Path("./training_data/processed/dataset_metadata.json")
    data_hash = None
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        data_hash = metadata['data_hash']
        logger.info(f"Training with data hash: {data_hash}")
        logger.info(f"Data timestamp: {metadata['timestamp']}")
        logger.info(f"Total samples: {metadata['total_samples']}")
    else:
        logger.warning("No dataset_metadata.json found. Training data may not be versioned.")

    # Load base model (using Phi-3-mini for Mac compatibility)
    model_key = "phi-3-mini"
    loader = ModelLoader(model_key=model_key, use_quantization=False) # Quantization false for Mac MPS

    tokenizer = loader.load_tokenizer()
    model = loader.load_model()

    # Initialize Trainer
    trainer = LoRATrainer(
        model=model,
        tokenizer=tokenizer,
        output_dir="./model_checkpoints",
        max_seq_length=1024 # Smaller sequence length for local Mac training
    )

    # Configure LoRA
    lora_config = trainer.get_lora_config(r=8, lora_alpha=16)

    # Check if we are doing a dry-run
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-steps", type=int, default=0, help="Max steps for dry run")
    args = parser.parse_args()

    # Configure Training Arguments
    training_args = trainer.get_training_arguments(
        num_train_epochs=1,
        per_device_train_batch_size=1, # Small batch size for Mac
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=1,
        save_steps=50,
        eval_steps=50
    )

    if args.max_steps > 0:
        training_args.max_steps = args.max_steps
        logger.info(f"Running dry-run for {args.max_steps} steps")

    # Start Training
    train_data = "./training_data/processed/train_processed_combined_training_data.json"
    val_data = "./training_data/processed/val_processed_combined_training_data.json"

    if not Path(train_data).exists():
        logger.error(f"Training data not found at {train_data}")
        sys.exit(1)

    # Load validation dataset for evaluation gate
    from datasets import Dataset
    if Path(val_data).exists():
        with open(val_data, "r") as f:
            val_data_list = json.load(f)
        eval_dataset = Dataset.from_list(val_data_list)
        logger.info(f"Loaded {len(eval_dataset)} validation samples for evaluation gate")
    else:
        eval_dataset = None
        logger.warning("No validation data found, skipping evaluation gate")

    trainer.train(
        train_data_path=train_data,
        val_data_path=val_data,
        lora_config=lora_config,
        training_args=training_args,
        data_hash=data_hash
    )

    # Post-training evaluation gate
    if eval_dataset is not None:
        logger.info("Running post-training evaluation gate...")
        post_eval_results = trainer.evaluate_model(eval_dataset, max_samples=10)
        logger.info(f"Post-training evaluation: {post_eval_results}")

        # Log warning if evaluation failed
        if post_eval_results.get("status") == "error":
            logger.warning("Post-training evaluation failed - model may have issues")

    logger.info("Local Fine-Tuning Completed Successfully!")

if __name__ == "__main__":
    main()
