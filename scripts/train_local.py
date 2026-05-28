import os
import sys
import logging
from pathlib import Path

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_training.model_loader import ModelLoader
from src.llm_training.lora_trainer import LoRATrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Local Fine-Tuning Pipeline...")

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

    trainer.train(
        train_data_path=train_data,
        val_data_path=val_data,
        lora_config=lora_config,
        training_args=training_args
    )
    
    logger.info("Local Fine-Tuning Completed Successfully!")

if __name__ == "__main__":
    main()
