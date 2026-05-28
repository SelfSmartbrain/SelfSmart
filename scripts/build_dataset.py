import asyncio
import logging
import sys
from pathlib import Path

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_training.data_collector import DataCollector
from src.llm_training.data_preprocessor import DataPreprocessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TECH_URLS = [
    "https://docs.python.org/3/tutorial/",
    "https://react.dev/learn",
    "https://nextjs.org/docs",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    "https://pytorch.org/tutorials/",
    "https://huggingface.co/docs/transformers/index",
    "https://kubernetes.io/docs/home/",
    "https://docs.docker.com/",
    "https://aws.amazon.com/blogs/machine-learning/",
    "https://cloud.google.com/blog/topics/developers-practitioners",
    "https://github.blog/category/engineering/",
    "https://engineering.fb.com/",
    "https://netflixtechblog.com/",
    "https://eng.uber.com/",
    "https://discord.com/blog/category/engineering"
]

async def main():
    logger.info("Step 1: Collecting training data from public web sources...")
    async with DataCollector() as collector:
        data = await collector.collect_all(
            wikipedia_count=50,
            hacker_news_count=50,
            urls=TECH_URLS
        )
    
    logger.info("Step 2: Preprocessing data into Instruction format...")
    preprocessor = DataPreprocessor(output_dir="./training_data/processed")
    processed_data = preprocessor.process_all(format_type="instruction")
    
    import json
    from pathlib import Path
    
    all_processed = []
    processed_dir = Path("./training_data/processed")
    for file in processed_dir.glob("processed_*.json"):
        if file.name == "processed_combined_training_data.json":
            continue
        with open(file, "r") as f:
            all_processed.extend(json.load(f))
            
    with open(processed_dir / "processed_combined_training_data.json", "w") as f:
        json.dump(all_processed, f, indent=2)
    
    # Split the dataset for training vs validation
    preprocessor.create_train_val_split("processed_combined_training_data.json")
    
    logger.info("Dataset creation complete. Output saved to ./training_data/processed/")

if __name__ == "__main__":
    asyncio.run(main())
