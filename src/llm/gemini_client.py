"""
Gemini API Client - Production-Grade Implementation
Handles Google Gemini API interactions with streaming and error recovery.
"""

import asyncio
import aiohttp
import time
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime
import json
from dataclasses import dataclass, field

from src.config.settings import get_settings
from src.utils.logging import get_logger
from src.utils.metrics import LLM_LATENCY, TOKEN_USAGE

logger = get_logger(__name__)

@dataclass
class Message:
    """Represents a conversation message"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMResponse:
    """Represents an LLM response"""
    content: str
    finish_reason: str
    usage: Dict[str, int]
    model: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: List[str] = field(default_factory=list)

class GeminiClient:
    """
    Production-grade Gemini API client.
    Handles the Google AI Studio / Gemini API specific format.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        
        if not self.api_key:
            logger.warning("Gemini API key not configured")
            raise ValueError("Gemini API key is required")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-1.5-flash"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = 60.0
        
        logger.info(f"Gemini client initialized with model: {self.model}")

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout, connect=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert standard messages to Gemini format"""
        formatted = []
        for msg in messages:
            role = "user" if msg.role in ["user", "system"] else "model"
            formatted.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        return formatted

    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """Send chat completion request to Gemini"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        contents = self._format_messages(messages)
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        start_time = time.time()
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gemini API error {response.status}: {error_text}")
            
            latency = time.time() - start_time
            LLM_LATENCY.labels(provider="gemini", model=self.model).observe(latency)

            data = await response.json()
            try:
                content = data['candidates'][0]['content']['parts'][0]['text']
                finish_reason = data['candidates'][0].get('finishReason', 'STOP')
                
                # Gemini usage metadata
                usage_metadata = data.get('usageMetadata', {})
                if usage_metadata:
                    TOKEN_USAGE.labels(provider="gemini", model=self.model, token_type="prompt").inc(usage_metadata.get("promptTokenCount", 0))
                    TOKEN_USAGE.labels(provider="gemini", model=self.model, token_type="completion").inc(usage_metadata.get("candidatesTokenCount", 0))

                return LLMResponse(
                    content=content,
                    finish_reason=finish_reason,
                    usage=usage_metadata,
                    model=self.model
                )
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to parse Gemini response: {e}")
                raise Exception("Unexpected response format from Gemini API")

    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion response from Gemini"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        contents = self._format_messages(messages)
        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Gemini Stream API error {response.status}: {error_text}")
            
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'candidates' in data and len(data['candidates']) > 0:
                            parts = data['candidates'][0].get('content', {}).get('parts', [])
                            for part in parts:
                                text = part.get('text', '')
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue
