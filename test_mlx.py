import asyncio
import sys
from pathlib import Path

# Ensure src modules are discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.llm_training.inference import LocalLLMClient

async def main():
    # Use a 4-bit quantized model to prevent Apple Silicon Out-Of-Memory errors
    client = LocalLLMClient(model_path="mlx-community/Phi-3-mini-4k-instruct-4bit")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in one simple sentence."}
    ]

    print("Testing MLX streaming on Apple Silicon...")
    async for chunk in client.generate_stream(messages, max_new_tokens=100):
        print(chunk, end="", flush=True)
    print("\n\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
