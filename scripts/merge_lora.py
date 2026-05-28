import os
import sys
import logging
from pathlib import Path

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_training.model_loader import ModelLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing LoRA Merging Pipeline...")

    model_key = "phi-3-mini"
    loader = ModelLoader(model_key=model_key, use_quantization=False)
    
    tokenizer = loader.load_tokenizer()
    
    logger.info("Loading Base Model...")
    base_model = loader.load_model()
    
    checkpoint_dir = Path("./model_checkpoints")
    
    if not checkpoint_dir.exists():
        logger.error(f"Checkpoint directory {checkpoint_dir} does not exist.")
        sys.exit(1)
        
    from peft import PeftModel
    
    # Try to find the latest checkpoint
    checkpoints = [d for d in checkpoint_dir.iterdir() if d.is_dir() and d.name.startswith("checkpoint")]
    if not checkpoints:
        logger.error("No checkpoints found.")
        sys.exit(1)
        
    latest_checkpoint = max(checkpoints, key=os.path.getmtime)
    logger.info(f"Loading LoRA weights from {latest_checkpoint}...")
    
    peft_model = PeftModel.from_pretrained(base_model, str(latest_checkpoint))
    
    logger.info("Merging weights into base model (this may take a while)...")
    merged_model = peft_model.merge_and_unload()
    
    output_dir = Path("./models/final_model")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving merged model to {output_dir}...")
    merged_model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    logger.info("Merge completed successfully!")

if __name__ == "__main__":
    main()
