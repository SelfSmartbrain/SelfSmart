"""
Local LLM Inference - Generate responses from fine-tuned models
Production-grade inference engine for local LLM deployment using MLX.
"""

import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """Represents an LLM response"""
    content: str
    finish_reason: str
    usage: Dict[str, int]
    model: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LocalLLMClient:
    """
    Production-grade local LLM client for inference.
    Supports loading fine-tuned models and streaming responses via mlx-lm.
    """

    def __init__(
        self,
        model_path: str,
        base_model_path: Optional[str] = None,
        use_quantization: bool = True,
        device: str = "auto"
    ):
        """
        Initialize local LLM client.

        Args:
            model_path: Path to fine-tuned model or base model
            base_model_path: Path to base model (ignored for MLX, we load the final merged model)
            use_quantization: Whether to use quantization (handled natively by MLX)
            device: Device to use (MLX defaults to MPS)
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None

        logger.info(f"Local MLX LLM client initialized for model: {model_path}")

    def load_model(self):
        """Load the model and tokenizer using mlx-lm."""
        logger.info(f"Loading MLX model from {self.model_path}")

        try:
            import mlx_lm
            self.model, self.tokenizer = mlx_lm.load(self.model_path)
            logger.info("MLX Model loaded successfully")
        except ImportError:
            logger.error("mlx-lm package is not installed. Please install it using `pip install mlx-lm`")
            raise

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        do_sample: bool = True
    ) -> LLMResponse:
        """
        Generate a response from the model.
        """
        if self.model is None:
            self.load_model()

        prompt = self._format_messages(messages)

        import mlx_lm

        # MLX generate
        generated_text = mlx_lm.generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_new_tokens,
            verbose=False
        )

        # mlx_lm.generate returns just the generated text
        return LLMResponse(
            content=generated_text.strip(),
            finish_reason="stop",
            usage={
                "prompt_tokens": len(prompt) // 4, # rough estimate
                "completion_tokens": len(generated_text) // 4,
                "total_tokens": (len(prompt) + len(generated_text)) // 4
            },
            model=self.model_path
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the model.
        """
        if self.model is None:
            self.load_model()

        prompt = self._format_messages(messages)

        import mlx_lm

        # mlx_lm.stream_generate yields chunks of text
        generator = mlx_lm.stream_generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_new_tokens
        )

        for chunk in generator:
            # Yield event loop control to allow FastAPI to stream back to client
            await asyncio.sleep(0.001)
            yield chunk

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages into a prompt string.
        """
        formatted = ""

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                formatted += f"### System:\n{content}\n\n"
            elif role == "user":
                formatted += f"### User:\n{content}\n\n"
            elif role == "assistant":
                formatted += f"### Assistant:\n{content}\n\n"

        formatted += "### Assistant:\n"
        return formatted

    def unload_model(self):
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        logger.info("Model unloaded, memory freed")
