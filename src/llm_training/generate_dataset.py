"""
Training Data Generator - Automated Fine-Tuning Pipeline
Converts raw conversational history and knowledge into Instruction-Context-Response triplets.
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from src.llm.conversation_manager import ConversationManager
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """
    Extracts high-quality conversational data for fine-tuning.
    """

    def __init__(
        self,
        conversation_manager: ConversationManager,
        output_dir: str = "./training_data/finetune",
    ):
        self.cm = conversation_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_dataset(self, limit: int = 1000):
        """Extract and format data for SFT (Supervised Fine-Tuning)"""
        # Load conversations from manager
        conversations = await self.cm.list_conversations(limit=limit)

        dataset = []
        for conv in conversations:
            # We assume a pattern: User-Assistant pairs are training samples
            # We only use conversations that were completed or deemed high-quality (could extend to filter by feedback.jsonl)
            conv_details = await self.cm.get_conversation(conv.id)
            messages = conv_details.messages

            for i in range(len(messages) - 1):
                if messages[i].role == "user" and messages[i + 1].role == "assistant":
                    dataset.append(
                        {
                            "instruction": messages[i].content,
                            "context": "",  # Could be filled from RAG retrieval history
                            "response": messages[i + 1].content,
                        }
                    )

        # Save to JSONL
        output_file = self.output_dir / "sft_dataset.jsonl"
        with open(output_file, "w") as f:
            for entry in dataset:
                f.write(json.dumps(entry) + "\n")

        logger.info(f"Generated SFT dataset with {len(dataset)} entries at {output_file}")
        return dataset


if __name__ == "__main__":
    # Minimal setup to run extraction
    cm = ConversationManager()
    gen = TrainingDataGenerator(cm)
    import asyncio

    asyncio.run(gen.generate_dataset())
