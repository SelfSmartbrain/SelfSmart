import os
import sys
import logging
import math
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from datasets import load_dataset

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_training.model_loader import ModelLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for evaluation gate
VALIDATION_DATA_PATH = "./training_data/processed/val_processed_combined_training_data.json"
ABSOLUTE_PPL_THRESHOLD = 20.0  # Perplexity threshold (lower is better)
REGRESSION_THRESHOLD = 0.1     # Allow up to 10% increase in perplexity compared to previous model

class TextDataset(Dataset):
    """Simple dataset for text data."""
    def __init__(self, texts: List[str], tokenizer: AutoTokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.texts = texts
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt"
        )
        return {k: v.squeeze(0) for k in encoding.items()}

def compute_perplexity(model: AutoModelForCausalLM, tokenizer: AutoTokenizer, data_path: str, batch_size: int = 4) -> float:
    """
    Compute perplexity of a model on a text dataset.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Evaluation data not found at {data_path}")

    # Load the dataset
    with open(data_path, "r") as f:
        data = json.load(f)

    # Extract text field (assuming format from the format used in training is "text" field )
    texts = [item["text"] for item in data]

    dataset = Dataset.from_dict({"text": texts})
    tokenized_dataset = dataset.map(
        lambda examples: tokenizer(
            examples["text"],
            truncation=True,
            max_length=512,
            padding="max_length"
        ),
        batched=True,
        remove_columns=["text"]
    )
    tokenized_dataset.set_format(type="torch", columns=["input_ids", "attention_mask"])

    dataloader = DataLoader(tokenized_dataset, batch_size=batch_size, shuffle=False)

    model.eval()
    total_loss = 0.0
    total_tokens = 0

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(model.device)
            attention_mask = batch["attention_mask"].to(model.device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=input_ids)
            loss = outputs.loss

            # Accumulate loss and token count
            batch_size = input_ids.size(0)
            seq_len = input_ids.size(1)
            total_loss += loss.item() * batch_size * seq_len
            total_tokens += batch_size * seq_len

    avg_loss = total_loss / total_tokens
    perplexity = math.exp(avg_loss)
    return perplexity

def load_eval_metrics(eval_path: str) -> Optional[Dict]:
    """
    Load evaluation metrics from a JSON file.
    """
    if not os.path.exists(eval_path):
        return None
    try:
        with open(eval_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load evaluation metrics from {eval_path}: {e}")
        return None

def save_eval_metrics(eval_path: str, metrics: Dict):
    """
    Save evaluation metrics to a JSON file.
    """
    os.makedirs(os.path.dirname(eval_path), exist_ok=True)
    with open(eval_path, "w") as f:
        json.dump(metrics, f, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model with evaluation gate.")
    parser.add_argument(
        "--model-checkpoint",
        type=str,
        default="./model_checkpoints/latest",
        help="Path to the LoRA checkpoint directory (default: ./model_checkpoints/latest)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models/fixed_model",
        help="Directory to save the merged model (default: ./models/fixed_model)"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="microsoft/Phi-3-mini-4k-instruct",
        help="Base model name or path (default: microsoft/Phi-3-mini-4k-instruct)"
    )
    parser.add_argument(
        "--eval-data-path",
        type=str,
        default=VALIDATION_DATA_PATH,
        help=f"Path to evaluation dataset (default: {VALIDATION_DATA_PATH})"
    )
    parser.add_argument(
        "--absolute-ppl-threshold",
        type=float,
        default=ABSOLUTE_PPL_THRESHOLD,
        help=f"Maximum allowed perplexity (lower is better, default: {ABSOLUTE_PPL_THRESHOLD})"
    )
    parser.add_argument(
        "--max-regression-ratio",
        type=float,
        default=REGRESSION_THRESHOLD,
        help=f"Maximum allowed increase in perplexity relative to previous model (e.g., 0.1 for 10%, default: {REGRESSION_THRESHOLD})"
    )
    args = parser.parse_args()

    logger.info("Starting LoRA merging with evaluation gate...")

    # Check evaluation data exists
    if not os.path.exists(args.eval_data_path):
        logger.error(f"Evaluation data not found at {args.eval_data_path}. Cannot run evaluation gate.")
        sys.exit(1)

    # Determine checkpoint directory
    checkpoint_dir = Path(args.model_checkpoint)
    if not checkpoint_dir.exists():
        # Try to find latest checkpoint in default location if provided path doesn't exist
        default_checkpoint_dir = Path("./model_checkpoints")
        if default_checkpoint_dir.exists():
            checkpoints = [d for d in default_checkpoint_dir.iterdir() if d.is_dir() and d.name.startswith("checkpoint")]
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=os.path.getmtime)
                checkpoint_dir = latest_checkpoint
                logger.warning(f"Provided checkpoint {args.model_checkpoint} not found. Using latest checkpoint: {checkpoint_dir}")
            else:
                logger.error(f"No checkpoints found in {default_checkpoint_dir} and provided path {args.model_checkpoint} does not exist.")
                sys.exit(1)
        else:
            logger.error(f"Checkpoint directory {args.model_checkpoint} does not exist and no default checkpoint directory found.")
            sys.exit(1)
    else:
        logger.info(f"Using checkpoint directory: {checkpoint_dir}")

    # Load base model and tokenizer
    logger.info(f"Loading base model: {args.base_model}")
    loader = ModelLoader(model_key=args.base_model, use_quantization=False)
    try:
        tokenizer = loader.load_tokenizer()
        base_model = loader.load_model()
    except Exception as e:
        logger.error(f"Failed to load base model {args.base_model}: {e}")
        sys.exit(1)

    # Load LoRA adapter and merge
    logger.info(f"Loading LoRA weights from {checkpoint_dir}...")
    try:
        peft_model = PeftModel.from_pretrained(base_model, str(checkpoint_dir))
    except Exception as e:
        logger.error(f"Failed to load LoRA adapter from {checkpoint_dir}: {e}")
        sys.exit(1)

    logger.info("Merging weights into base model (this may take a while)...")
    try:
        merged_model = peft_model.merge_and_unload()
    except Exception as e:
        logger.error(f"Failed to merge LoRA weights: {e}")
        sys.exit(1)

    # Evaluate merged model on validation set
    logger.info(f"Evaluating merged model on {args.eval_data_path}...")
    try:
        perplexity = compute_perplexity(merged_model, tokenizer, args.eval_data_path)
        logger.info(f"Perplexity on validation set: {perplexity:.4f}")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)

    # Check if there is a previous model to compare against
    eval_metrics_path = os.path.join(args.output_dir, "eval_metrics.json")
    prev_metrics = load_eval_metrics(eval_metrics_path)
    prev_perplexity = None
    if prev_metrics and "perplexity" in prev_metrics:
        prev_perplexity = float(prev_metrics["perplexity"])
        logger.info(f"Previous model perplexity: {prev_perplexity:.4f}")

    # Evaluation gate checks
    passed = True
    reason = []

    # Check absolute threshold
    if perplexity > args.absolute_ppl_threshold:
        passed = False
        reason.append(f"Perplexity {perplexity:.4f} exceeds absolute threshold {args.absolute_ppl_threshold}")

    # Check regression against previous model
    if prev_perplexity is not None:
        allowed_increase = prev_perplexity * (1 + args.max_regression_ratio)
        if perplexity > allowed_increase:
            passed = False
            reason.append(f"Perplexity {perplexity:.4f} is more than {args.max_regression_ratio*100}% worse than previous model {prev_perplexity:.4f} (allowed: {allowed_increase:.4f})")

    if passed:
        logger.info("Evaluation gate PASSED.")
        # Save merged model
        os.makedirs(args.output_dir, exist_ok=True)
        try:
            merged_model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)
            logger.info(f"Merged model saved to {args.output_dir}")
        except Exception as e:
            logger.error(f"Failed to save merged model: {e}")
            sys.exit(1)

        # Save evaluation metrics
        eval_metrics = {
            "perplexity": float(perplexity),
            "eval_dataset": args.eval_data_path,
            "eval_timestamp": None,  # Will set below
            "model_base": args.base_model,
            "lora_checkpoint": str(checkpoint_dir)
        }
        from datetime import datetime
        eval_metrics["eval_timestamp"] = datetime.now().isoformat()
        save_eval_metrics(eval_metrics_path, eval_metrics)
        logger.info(f"Evaluation metrics saved to {eval_metrics_path}")
    else:
        logger.error("Evaluation gate FAILED.")
        for r in reason:
            logger.error(f"  - {r}")
        sys.exit(1)

if __name__ == "__main__":
    main()