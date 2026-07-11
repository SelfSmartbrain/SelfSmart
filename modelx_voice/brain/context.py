import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .llm_client import LLMProvider, Message, get_default_model, get_provider

logger = logging.getLogger(__name__)


@dataclass
class ConversationExchange:
    user: str
    assistant: str
    timestamp: float
    tokens_used: dict[str, int] | None = None


class ConversationMemory:
    def __init__(
        self,
        max_turns: int = 20,
        max_tokens: int = 8000,
        persistence_file: Path | None = None,
    ):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.persistence_file = persistence_file
        self.history: deque[ConversationExchange] = deque(maxlen=max_turns)
        self._total_tokens = 0

        if persistence_file and persistence_file.exists():
            self.load()

    def add_exchange(
        self,
        user_input: str,
        ai_response: str,
        tokens_used: dict[str, int] | None = None,
    ):
        exchange = ConversationExchange(
            user=user_input,
            assistant=ai_response,
            timestamp=time.time(),
            tokens_used=tokens_used,
        )
        self.history.append(exchange)

        if tokens_used:
            self._total_tokens += tokens_used.get("input_tokens", 0) + tokens_used.get(
                "output_tokens", 0
            )

        self._prune_by_tokens()

        if self.persistence_file:
            self.save()

    def _prune_by_tokens(self):
        while self._total_tokens > self.max_tokens and len(self.history) > 1:
            removed = self.history.popleft()
            if removed.tokens_used:
                self._total_tokens -= removed.tokens_used.get(
                    "input_tokens", 0
                ) + removed.tokens_used.get("output_tokens", 0)

        if self._total_tokens > self.max_tokens and self.history:
            removed = self.history.popleft()
            if removed.tokens_used:
                self._total_tokens -= removed.tokens_used.get("input_tokens", 0)
                self._total_tokens -= removed.tokens_used.get("output_tokens", 0)

    def get_context(self, recent_turns: int = 5) -> list[Message]:
        recent = list(self.history)[-recent_turns:]
        messages = []
        for exchange in recent:
            messages.append(Message(role="user", content=exchange.user))
            messages.append(Message(role="assistant", content=exchange.assistant))
        return messages

    def get_full_history(self) -> list[ConversationExchange]:
        return list(self.history)

    def save(self):
        if self.persistence_file:
            data = {
                "history": [asdict(ex) for ex in self.history],
                "total_tokens": self._total_tokens,
            }
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

    def load(self):
        if self.persistence_file and self.persistence_file.exists():
            with open(self.persistence_file) as f:
                data = json.load(f)
            self.history = deque(
                [ConversationExchange(**ex) for ex in data.get("history", [])],
                maxlen=self.max_turns,
            )
            self._total_tokens = data.get("total_tokens", 0)

    def clear(self):
        self.history.clear()
        self._total_tokens = 0
        if self.persistence_file and self.persistence_file.exists():
            self.persistence_file.unlink()

    def export_conversation(self, export_path: Path) -> None:
        """Export the current conversation without exposing configuration secrets."""
        export_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "exchanges": [asdict(exchange) for exchange in self.history],
            "total_tokens": self._total_tokens,
        }
        with open(export_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    @property
    def estimated_tokens(self) -> int:
        """Backward-compatible name for the tracked provider token total."""
        return self._total_tokens

    @property
    def turn_count(self) -> int:
        return len(self.history)


class ModelXBrain:
    def __init__(
        self,
        provider: str,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        memory: ConversationMemory = None,
        system_prompt: str = None,
    ):
        self.provider_name = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model = model or get_default_model(provider)
        self.memory = memory or ConversationMemory()
        self.system_prompt = system_prompt or self._default_system_prompt()
        self._provider: LLMProvider = None
        self._initialized = False

    def _default_system_prompt(self) -> str:
        return """You are ModelX, a helpful voice assistant.
Keep responses conversational, concise, and natural for voice interaction.
Avoid markdown formatting, bullet points, or code blocks unless explicitly asked.
Speak naturally as if having a conversation."""

    def _get_provider(self) -> LLMProvider:
        if self._provider is None:
            self._provider = get_provider(self.provider_name, self.api_key, self.base_url)
        return self._provider

    async def process_input(self, user_text: str) -> str:
        provider = self._get_provider()

        messages = [Message(role="system", content=self.system_prompt)]
        messages.extend(self.memory.get_context(recent_turns=10))
        messages.append(Message(role="user", content=user_text))

        response = await provider.chat_completion(
            messages=messages,
            model=self.model,
            max_tokens=1000,
            temperature=0.7,
        )

        self.memory.add_exchange(
            user_input=user_text,
            ai_response=response.content,
            tokens_used=response.usage,
        )

        return response.content

    async def stream_response(self, user_text: str):
        provider = self._get_provider()

        messages = [Message(role="system", content=self.system_prompt)]
        messages.extend(self.memory.get_context(recent_turns=10))
        messages.append(Message(role="user", content=user_text))

        full_response = ""
        async for chunk in provider.stream_chat_completion(
            messages=messages,
            model=self.model,
            max_tokens=1000,
            temperature=0.7,
        ):
            full_response += chunk
            yield chunk

        self.memory.add_exchange(
            user_input=user_text,
            ai_response=full_response,
        )

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt

    def clear_memory(self):
        self.memory.clear()

    def get_stats(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "turns": self.memory.turn_count,
            "total_tokens": self.memory.total_tokens,
        }

    async def close(self):
        if self._provider:
            await self._provider.close()
            self._provider = None
