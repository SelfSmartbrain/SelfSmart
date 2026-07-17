"""Shared runtime state for SelfSmart chat, RAG, and learning endpoints."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

from src.api.free_api_client import FreeAPIClient
from src.config.settings import get_settings
from src.learning.continuous_learner import ContinuousLearner, LearningConfig
from src.llm.agent_tools import ToolExecutor
from src.llm.conversation_manager import ConversationManager
from src.llm.deepseek_client import DeepSeekClient
from src.llm.gemini_client import GeminiClient
from src.llm.rag_service import RAGService
from src.llm_training.inference import LocalLLMClient

settings = get_settings()
SERVER_START_TIME = time.time()

learning_config = LearningConfig()
learner = ContinuousLearner(learning_config)
free_api_client = FreeAPIClient()
conversation_manager = ConversationManager()
rag_service = RAGService()
tool_executor = ToolExecutor()

_learning_active: bool = False
_learning_task: Optional[asyncio.Task] = None

local_llm_client: Optional[LocalLLMClient] = None
use_local_llm = settings.use_local_llm


def llm_api_key_configured() -> bool:
    provider = (settings.llm_provider or "deepseek").lower()
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    return bool(settings.deepseek_api_key)


def get_llm_client():
    if settings.llm_provider.lower() == "gemini":
        return GeminiClient()
    return DeepSeekClient()


async def prewarm_local_llm() -> None:
    global local_llm_client, use_local_llm
    if not use_local_llm:
        return
    try:
        local_llm_client = LocalLLMClient(
            model_path="./model_checkpoints",
            base_model_path="mistralai/Mistral-7B-v0.1",
        )
        local_llm_client.load_model()
    except Exception:
        use_local_llm = False


def allowed_origins() -> list[str]:
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ]
