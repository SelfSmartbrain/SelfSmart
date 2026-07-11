import asyncio
import logging
import random
import numpy as np
import torch
import json
import hashlib
from pathlib import Path
from datetime import datetime
from src.tasks.celery_app import app
from src.llm_training.data_collector import DataCollector
from src.llm_training.data_preprocessor import DataPreprocessor
from src.llm_training.model_loader import ModelLoader
from src.llm_training.lora_trainer import LoRATrainer
from transformers import TrainingArguments

logger = logging.getLogger(__name__)

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

async def _run_training_pipeline():
    """Async function to run the full LoRA fine-tuning pipeline."""
    # 1. Collect training data
    logger.info("Step 1: Collecting training data...")
    async with DataCollector() as collector:
        data = await collector.collect_all(wikipedia_count=100000, hacker_news_count=100)

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

    # 3. Load model
    logger.info("Step 3: Loading base model...")
    model_loader = ModelLoader(model_key="phi-3-mini", use_quantization=False)
    model = model_loader.load_model()
    tokenizer = model_loader.load_tokenizer()

    # 4. Fine-tune
    logger.info("Step 4: Fine-tuning...")
    trainer = LoRATrainer(model, tokenizer, output_dir="./model_checkpoints")

    training_args = TrainingArguments(
        output_dir="./model_checkpoints",
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        save_steps=100,
        eval_steps=100,
        evaluation_strategy="steps",
        fp16=False,
        bf16=True,  # MPS/M1 optimization
        optim="adamw_torch"
    )

    trainer.train(
        train_data_path="./training_data/processed/train_processed_combined_training_data.json",
        val_data_path="./training_data/processed/val_processed_combined_training_data.json",
        lora_config=None,  # Use default LoRA config
        training_args=training_args,
        data_hash=data_hash
    )

@app.task(bind=True, name="src.tasks.training_tasks.run_model_training")
def run_model_training(self):
    """Celery task to run the full LoRA fine-tuning pipeline."""
    logger.info("Starting model training task...")

    # Set random seed for reproducibility
    set_seed(seed=42)

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_run_training_pipeline())
        return {"status": "completed", "output_dir": "./model_checkpoints"}
    except Exception as e:
        logger.error(f"Training task failed: {e}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e
