"""
Build DPO Dataset - Converts User Feedback into Preference Pairs
Synthesizes 'chosen' and 'rejected' responses using LLM where missing.
"""

import json
import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

import sys
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.llm.gemini_client import GeminiClient, Message
from src.llm.conversation_manager import ConversationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def synthesize_chosen(prompt: str, rejected: str, client: GeminiClient) -> str:
    """Generate a high-quality chosen response to replace a bad rejected one."""
    messages = [
        Message(role="system", content="You are an expert AI assistant. A previous AI generated a poor response to the user's prompt. Provide a perfect, highly-detailed, and accurate response to the prompt."),
        Message(role="user", content=f"User Prompt: {prompt}\n\nBad AI Response: {rejected}\n\nPlease write a superior response:")
    ]
    response = await client.chat(messages)
    return response.content

async def synthesize_rejected(prompt: str, chosen: str, client: GeminiClient) -> str:
    """Generate a poor/hallucinated rejected response to pair with a good chosen one."""
    messages = [
        Message(role="system", content="You are a bad AI assistant. Give a plausible but slightly incorrect, unhelpful, or overly generic response to the prompt. Do not admit you are bad, just fail subtly."),
        Message(role="user", content=f"User Prompt: {prompt}\n\nPlease write a subpar response:")
    ]
    response = await client.chat(messages)
    return response.content

async def build_dataset():
    load_dotenv()
    
    data_dir = project_root / "data"
    feedback_file = data_dir / "feedback.jsonl"
    output_file = project_root / "training_data" / "processed" / "dpo_dataset.json"
    
    if not feedback_file.exists():
        logger.error(f"Feedback file not found at {feedback_file}")
        
        # Create mock feedback for testing if none exists
        logger.info("Creating mock feedback for DPO verification...")
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(feedback_file, "w") as f:
            f.write(json.dumps({"conversation_id": "mock_1", "message_index": 2, "is_positive": False, "comment": "Too generic"}) + "\n")
            f.write(json.dumps({"conversation_id": "mock_2", "message_index": 2, "is_positive": True, "comment": "Great answer!"}) + "\n")
    
    # Initialize DB
    cm = ConversationManager()
    
    async with GeminiClient() as gemini:
        logger.info("Reading feedback...")
        feedbacks = []
        with open(feedback_file, 'r') as f:
            for line in f:
                if line.strip():
                    feedbacks.append(json.loads(line))
                    
        dpo_pairs = []
        
        for fb in feedbacks:
            conv_id = fb['conversation_id']
            idx = fb['message_index']
            is_pos = fb['is_positive']
            
            # If mock, hardcode values
            if conv_id.startswith("mock_"):
                prompt = "What is machine learning?" if conv_id == "mock_1" else "Explain Newton's laws."
                original_response = "Machine learning is computers." if conv_id == "mock_1" else "Newton has 3 laws of motion describing gravity and force."
            else:
                # Fetch from DB
                conv = await cm.get_conversation(conv_id)
                if not conv or len(conv.messages) <= idx:
                    continue
                    
                prompt_msg = conv.messages[idx - 1] if idx > 0 else None
                response_msg = conv.messages[idx]
                
                if not prompt_msg or prompt_msg.role != 'user' or response_msg.role != 'assistant':
                    continue
                    
                prompt = prompt_msg.content
                original_response = response_msg.content
                
            logger.info(f"Processing feedback for prompt: {prompt[:50]}...")
            
            if is_pos:
                # original is chosen, synthesize rejected
                chosen = original_response
                rejected = await synthesize_rejected(prompt, chosen, gemini)
            else:
                # original is rejected, synthesize chosen
                rejected = original_response
                chosen = await synthesize_chosen(prompt, rejected, gemini)
                
            dpo_pairs.append({
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected
            })
            
            # Don't hit rate limits
            await asyncio.sleep(2)
            
        # Save output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(dpo_pairs, f, indent=2)
            
        logger.info(f"✅ Created DPO dataset with {len(dpo_pairs)} pairs at {output_file}")

if __name__ == "__main__":
    asyncio.run(build_dataset())
