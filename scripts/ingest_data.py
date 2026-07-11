import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
import hashlib
import sys
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge.knowledge_integrator import KnowledgeIntegrator
from src.processor.content_processor import ProcessedContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_raw_data(data_dir: Path) -> list:
    """Load all JSON files in the raw training data directory."""
    all_data = []
    for json_file in data_dir.glob("*.json"):
        # Skip preprocessed files
        if json_file.name.startswith("processed_") or json_file.name.startswith("train_") or json_file.name.startswith("val_"):
            continue
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                all_data.extend(file_data)
                logger.info(f"Loaded {len(file_data)} items from {json_file.name}")
        except Exception as e:
            logger.error(f"Error reading {json_file}: {e}")
    return all_data

def process_item_with_chunking(item: dict, text_splitter: RecursiveCharacterTextSplitter) -> list[ProcessedContent]:
    url = item.get("url", "")
    content = item.get("content", "")
    if not content:
        return []

    chunks = text_splitter.split_text(content)
    processed_contents = []

    for idx, chunk in enumerate(chunks):
        content_id = hashlib.sha256(f"{url}_{idx}".encode() if url else str(chunk).encode()).hexdigest()[:16]

        timestamp_str = item.get("timestamp")
        try:
            timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
        except ValueError:
            timestamp = datetime.utcnow()

        processed_contents.append(
            ProcessedContent(
                id=content_id,
                title=f"{item.get('title', 'Untitled')} (Part {idx+1})",
                content=chunk,
                summary=chunk[:200] + "...",
                topics=[],
                entities=[],
                quality_score=0.9,
                relevance_score=0.9,
                language="en",
                metadata={
                    "source_url": url,
                    "source_type": item.get("source", "unknown"),
                    "chunk_idx": idx,
                    "total_chunks": len(chunks)
                },
                timestamp=timestamp
            )
        )
    return processed_contents

async def main():
    data_dir = Path("./training_data")
    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} does not exist. Run build_dataset.py first.")
        return

    logger.info("Loading raw collected dataset...")
    raw_data = load_raw_data(data_dir)
    if not raw_data:
        logger.warning("No raw data found to ingest.")
        return

    logger.info(f"Chunking {len(raw_data)} items to ProcessedContent...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    processed_contents = []
    for item in raw_data:
        processed_contents.extend(process_item_with_chunking(item, text_splitter))

    logger.info("Initializing Knowledge Integrator...")
    ki = KnowledgeIntegrator()

    logger.info(f"Ingesting {len(processed_contents)} documents into Vector Store...")
    await ki.batch_integrate(processed_contents)

    logger.info("Ingestion complete. RAG is now ready.")

if __name__ == "__main__":
    asyncio.run(main())
