"""
LLM Module for SmartSelf AI
Production-grade LLM integration with streaming and context management.
"""

from src.llm.deepseek_client import DeepSeekClient
from src.llm.gemini_client import GeminiClient
from src.llm.rag_service import RAGService
from src.llm.conversation_manager import ConversationManager
from src.llm.local_client import (
    LocalModelClient,
    LocalBackend,
    OllamaClient,
    LlamaCppClient,
    VLLMClient,
    TransformersClient,
    OpenAICompatibleClient,
    Message,
    LLMResponse,
    quick_chat,
    quick_stream,
    detect_available_backends,
    recommend_backend,
)

__all__ = [
    "DeepSeekClient",
    "GeminiClient",
    "RAGService",
    "ConversationManager",
    "LocalModelClient",
    "LocalBackend",
    "OllamaClient",
    "LlamaCppClient",
    "VLLMClient",
    "TransformersClient",
    "OpenAICompatibleClient",
    "Message",
    "LLMResponse",
    "quick_chat",
    "quick_stream",
    "detect_available_backends",
    "recommend_backend",
]
