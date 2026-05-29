"""
Train DPO - Local execution script for Direct Preference Optimization
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.llm_training.dpo_trainer import DPOTrainerManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    dataset_path = project_root / "training_data" / "processed" / "dpo_dataset.json"
    
    if not dataset_path.exists():
        logger.error(f"DPO dataset not found at {dataset_path}. Run `build_dpo_dataset.py` first.")
        sys.exit(1)
        
    with open(dataset_path, "r") as f:
        dpo_pairs = json.load(f)
        
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
        logger.info("✅ DPO Training completed successfully!")
    except Exception as e:
        logger.error(f"❌ DPO Training failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
