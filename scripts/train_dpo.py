"""
Train DPO - Local execution script for Direct Preference Optimization
"""
 
import sys
import os
import json
import random
import numpy as np
import torch
import hashlib
from datetime import datetime
from pathlib import Path
 
# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
 
from src.llm_training.dpo_trainer import DPOTrainerManager
import logging
 
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
    """Compute SHA256 hash of data for versioning."""
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()[:16]
 
def main():
    # Set random seed for reproducibility
    set_seed(seed=42)
 
    # Check data version for reproducibility (SFT data hash, if available)
    sft_metadata_path = project_root / "training_data" / "processed" / "dataset_metadata.json"
    if sft_metadata_path.exists():
        with open(sft_metadata_path, "r") as f:
            metadata = json.load(f)
        logger.info(f"SFT data hash: {metadata['data_hash']}")
        logger.info(f"SFT data timestamp: {metadata['timestamp']}")
    else:
        logger.warning("No SFT dataset_metadata.json found. SFT data may not be versioned.")
 
    dataset_path = project_root / "training_data" / "processed" / "dpo_dataset.json"
 
    if not dataset_path.exists():
        logger.error(f"DPO dataset not found at {dataset_path}. Run `build_dpo_dataset.py` first.")
        sys.exit(1)
 
    with open(dataset_path, "r") as f:
        dpo_pairs = json.load(f)
 
    # Compute hash of DPO dataset for versioning
    dpo_data_hash = compute_data_hash(dpo_pairs)
    dpo_metadata = {
        "dpo_data_hash": dpo_data_hash,
        "timestamp": datetime.utcnow().isoformat(),
        "num_pairs": len(dpo_pairs),
        "sources": ["feedback"]  # DPO data comes from feedback
    }
 
    logger.info(f"DPO dataset hash: {dpo_data_hash}")
 
    logger.info(f"Loaded {len(dpo_pairs)} DPO pairs for training.")
 
    # Check for existing fine-tuned model
    fine_tuned_path = project_root / "models" / "final_model"
 
    # If the user merged the previous SFT model, we DPO that model.
    # Otherwise, fallback to base Phi-3.
    model_name = str(fine_tuned_path) if fine_tuned_path.exists() else "microsoft/Phi-3-mini-4k-instruct"
 
    logger.info(f"Using base model for DPO: {model_name}")
 
    manager = DPOTrainerManager(
        model_name=model_name,
        output_dir="./models/dpo_checkpoints",
        use_4bit=False # False for Mac MPS, True for Kaggle
    )
 
    try:
        manager.train(dpo_pairs)
 
        # Save DPO dataset metadata to the output directory
        output_dir = Path("./models/dpo_checkpoints")
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = output_dir / "dataset_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(dpo_metadata, f, indent=2)
        logger.info(f"DPO dataset metadata saved to {metadata_path}")
 
        logger.info("✅ DPO Training completed successfully!")
    except Exception as e:
        logger.error(f"❌ DPO Training failed: {e}", exc_info=True)
 
if __name__ == "__main__":
    main()
