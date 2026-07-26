"""
Local Model Client - Unified interface for running open-weight models locally.

Supports multiple backends:
- Ollama (easiest setup)
- llama.cpp (fast CPU inference)
- vLLM (high-throughput GPU)
- Transformers (direct Python)
- Any OpenAI-compatible server
"""

import asyncio
import aiohttp
import time
import json
import subprocess
import os
from typing import AsyncGenerator, Optional, Dict, Any, List, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.monitoring.prometheus import LLM_LATENCY, TOKEN_USAGE

logger = get_logger(__name__)


class LocalBackend(str, Enum):
    """Supported local inference backends"""
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    VLLM = "vllm"
    TRANSFORMERS = "transformers"
    OPENAI_COMPATIBLE = "openai_compatible"


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


class BaseLocalClient(ABC):
    """Abstract base for local model clients"""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion request"""
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources"""
        pass
    
    def _to_api_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert Message objects to API format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]


class OllamaClient(BaseLocalClient):
    """Ollama local inference client"""
    
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=kwargs.get('timeout', 300))
    
    async def initialize(self) -> None:
        """Initialize Ollama client and verify model exists"""
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # Check if Ollama is running
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Ollama not responding: {resp.status}")
                    
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]
                    if self.model not in models:
                        logger.warning(f"Model {self.model} not found locally. Available: {models}")
                        logger.info(f"Pull with: ollama pull {self.model}")
                
                self._initialized = True
                logger.info(f"Ollama client initialized for model: {self.model}")
                
            except aiohttp.ClientConnectorError:
                raise RuntimeError(
                    f"Cannot connect to Ollama at {self.base_url}. "
                    f"Start with: ollama serve"
                )
    
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        api_messages = self._to_api_messages(messages)
        
        payload = {
            "model": self.model,
            "messages": api_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": kwargs.get('top_p', 0.9),
                "top_k": kwargs.get('top_k', 40),
                "repeat_penalty": kwargs.get('repeat_penalty', 1.1),
            }
        }
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise RuntimeError(f"Ollama error {resp.status}: {error}")
                
                data = await resp.json()
                latency = time.time() - start_time
                
                LLM_LATENCY.labels(provider="ollama", model=self.model).observe(latency)
                
                return LLMResponse(
                    content=data.get('message', {}).get('content', ''),
                    finish_reason=data.get('done_reason', 'stop'),
                    usage={
                        'prompt_tokens': data.get('prompt_eval_count', 0),
                        'completion_tokens': data.get('eval_count', 0),
                        'total_tokens': data.get('prompt_eval_count', 0) + data.get('eval_count', 0)
                    },
                    model=self.model
                )
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        api_messages = self._to_api_messages(messages)
        payload = {
            "model": self.model,
            "messages": api_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        async with self.session.post(f"{self.base_url}/api/chat", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"Ollama stream error: {error}")
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get('message', {}).get('content', '')
                    if content:
                        yield content
                    if data.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue
    
    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None


class LlamaCppClient(BaseLocalClient):
    """llama.cpp server client (OpenAI-compatible API)"""
    
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8080",
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{self.base_url}/v1/models") as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"llama.cpp server not responding: {resp.status}")
                self._initialized = True
                logger.info(f"llama.cpp client initialized: {self.model}")
            except aiohttp.ClientConnectorError:
                raise RuntimeError(
                    f"Cannot connect to llama.cpp server at {self.base_url}. "
                    f"Start with: llama-server -m <model.gguf> --port 8080"
                )
    
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "model": self.model,
            "messages": self._to_api_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }
        
        start_time = time.time()
        async with self.session.post(f"{self.base_url}/v1/chat/completions", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"llama.cpp error {resp.status}: {error}")
            
            data = await resp.json()
            latency = time.time() - start_time
            LLM_LATENCY.labels(provider="llama_cpp", model=self.model).observe(latency)
            
            choice = data['choices'][0]
            usage = data.get('usage', {})
            
            return LLMResponse(
                content=choice['message']['content'],
                finish_reason=choice.get('finish_reason', 'stop'),
                usage=usage,
                model=self.model
            )
    
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        payload = {
            "model": self.model,
            "messages": self._to_api_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }
        
        async with self.session.post(f"{self.base_url}/v1/chat/completions", json=payload) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"llama.cpp stream error: {error}")
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if not line or line == 'data: [DONE]':
                    continue
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        delta = data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def close(self) -> None:
        if self.session:
            await self.session.close()


class VLLMClient(LlamaCppClient):
    """vLLM client (same OpenAI-compatible API as llama.cpp)"""
    
    async def initialize(self) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{self.base_url}/v1/models") as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"vLLM server not responding: {resp.status}")
                self._initialized = True
                logger.info(f"vLLM client initialized: {self.model}")
            except aiohttp.ClientConnectorError:
                raise RuntimeError(
                    f"Cannot connect to vLLM at {self.base_url}. "
                    f"Start with: python -m vllm.entrypoints.openai.api_server --model <path>"
                )


class TransformersClient(BaseLocalClient):
    """Direct transformers inference (requires GPU)"""
    
    def __init__(
        self,
        model: str,
        device: str = "auto",
        torch_dtype: str = "auto",
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.device = device
        self.torch_dtype = torch_dtype
        self._model = None
        self._tokenizer = None
        self._generation_config = None
    
    async def initialize(self) -> None:
        """Load model and tokenizer"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
            
            logger.info(f"Loading transformers model: {self.model}")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Load model
            dtype = getattr(torch, self.torch_dtype) if self.torch_dtype != "auto" else "auto"
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model,
                torch_dtype=dtype,
                device_map=self.device,
                low_cpu_mem_usage=True,
            )
            
            self._generation_config = GenerationConfig.from_pretrained(self.model)
            self._initialized = True
            logger.info(f"Transformers model loaded on {self._model.device}")
            
        except ImportError:
            raise RuntimeError("transformers not installed. pip install transformers torch accelerate")
        except Exception as e:
            logger.error(f"Failed to load transformers model: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        if not self._initialized:
            await self.initialize()
        
        import torch
        
        # Apply chat template
        prompt = self._tokenizer.apply_chat_template(
            self._to_api_messages(messages),
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        
        generation_config = self._generation_config
        generation_config.temperature = temperature
        generation_config.max_new_tokens = max_tokens
        generation_config.do_sample = temperature > 0
        generation_config.top_p = kwargs.get('top_p', 0.9)
        generation_config.top_k = kwargs.get('top_k', 40)
        generation_config.repetition_penalty = kwargs.get('repeat_penalty', 1.1)
        generation_config.pad_token_id = self._tokenizer.pad_token_id
        generation_config.eos_token_id = self._tokenizer.eos_token_id
        
        start_time = time.time()
        
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                generation_config=generation_config,
            )
        
        latency = time.time() - start_time
        LLM_LATENCY.labels(provider="transformers", model=self.model).observe(latency)
        
        # Decode only new tokens
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        content = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        
        return LLMResponse(
            content=content,
            finish_reason="stop",
            usage={
                'prompt_tokens': inputs['input_ids'].shape[1],
                'completion_tokens': new_tokens.shape[0],
                'total_tokens': outputs.shape[1]
            },
            model=self.model
        )
    
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        # Transformers streaming requires TextIteratorStreamer in separate thread
        # Simplified implementation - yields full response
        response = await self.chat(messages, temperature, max_tokens, **kwargs)
        yield response.content
    
    async def close(self) -> None:
        import torch
        if self._model:
            del self._model
            torch.cuda.empty_cache()
        self._model = None
        self._tokenizer = None


class OpenAICompatibleClient(LlamaCppClient):
    """Generic OpenAI-compatible API client"""
    
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "not-needed",
        **kwargs
    ):
        super().__init__(model, base_url, **kwargs)
        self.api_key = api_key
    
    async def initialize(self) -> None:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key != "not-needed" else {}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                async with session.get(f"{self.base_url}/v1/models") as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"Server not responding: {resp.status}")
                self._initialized = True
                logger.info(f"OpenAI-compatible client initialized: {self.model}")
            except aiohttp.ClientConnectorError:
                raise RuntimeError(f"Cannot connect to {self.base_url}")


class LocalModelClient:
    """
    Unified factory and manager for local model clients.
    Automatically detects available backends and provides unified interface.
    """
    
    def __init__(self):
        self._client: Optional[BaseLocalClient] = None
        self._backend: Optional[LocalBackend] = None
        self._model: Optional[str] = None
    
    @classmethod
    async def create(
        cls,
        model: str,
        backend: Union[LocalBackend, str] = LocalBackend.OLLAMA,
        **kwargs
    ) -> "LocalModelClient":
        """Factory method to create and initialize client"""
        instance = cls()
        await instance.initialize(model, backend, **kwargs)
        return instance
    
    async def initialize(
        self,
        model: str,
        backend: Union[LocalBackend, str] = LocalBackend.OLLAMA,
        **kwargs
    ) -> None:
        """Initialize the appropriate backend client"""
        if isinstance(backend, str):
            backend = LocalBackend(backend.lower())
        
        self._model = model
        self._backend = backend
        
        client_map = {
            LocalBackend.OLLAMA: OllamaClient,
            LocalBackend.LLAMA_CPP: LlamaCppClient,
            LocalBackend.VLLM: VLLMClient,
            LocalBackend.TRANSFORMERS: TransformersClient,
            LocalBackend.OPENAI_COMPATIBLE: OpenAICompatibleClient,
        }
        
        client_class = client_map.get(backend)
        if not client_class:
            raise ValueError(f"Unsupported backend: {backend}")
        
        self._client = client_class(model, **kwargs)
        await self._client.initialize()
        logger.info(f"Initialized {backend.value} client for model: {model}")
    
    @property
    def model(self) -> str:
        return self._model or ""
    
    @property
    def backend(self) -> Optional[LocalBackend]:
        return self._backend
    
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion"""
        if not self._client:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        return await self._client.chat(messages, temperature, max_tokens, stream, **kwargs)
    
    async def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion"""
        if not self._client:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        async for chunk in self._client.chat_stream(messages, temperature, max_tokens, **kwargs):
            yield chunk
    
    async def close(self) -> None:
        """Cleanup resources"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def __aenter__(self) -> "LocalModelClient":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# Convenience functions
async def quick_chat(
    model: str,
    prompt: str,
    backend: Union[LocalBackend, str] = LocalBackend.OLLAMA,
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """Quick one-off chat completion"""
    messages = []
    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))
    messages.append(Message(role="user", content=prompt))
    
    async with await LocalModelClient.create(model, backend, **kwargs) as client:
        response = await client.chat(messages, **kwargs)
        return response.content


async def quick_stream(
    model: str,
    prompt: str,
    backend: Union[LocalBackend, str] = LocalBackend.OLLAMA,
    system_prompt: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[str, None]:
    """Quick streaming chat"""
    messages = []
    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))
    messages.append(Message(role="user", content=prompt))
    
    async with await LocalModelClient.create(model, backend, **kwargs) as client:
        async for chunk in client.chat_stream(messages, **kwargs):
            yield chunk


# Auto-detect available backend
async def detect_available_backends() -> Dict[LocalBackend, bool]:
    """Check which backends are available"""
    results = {}
    
    # Check Ollama
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get("http://localhost:11434/api/tags") as resp:
                results[LocalBackend.OLLAMA] = resp.status == 200
    except Exception:
        results[LocalBackend.OLLAMA] = False
    
    # Check llama.cpp / vLLM / OpenAI-compatible on common ports
    for backend, port in [
        (LocalBackend.LLAMA_CPP, 8080),
        (LocalBackend.VLLM, 8000),
        (LocalBackend.OPENAI_COMPATIBLE, 8000),
    ]:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                async with session.get(f"http://localhost:{port}/v1/models") as resp:
                    results[backend] = resp.status == 200
        except Exception:
            results[backend] = False
    
    # Transformers always "available" if torch installed
    try:
        import torch
        results[LocalBackend.TRANSFORMERS] = True
    except ImportError:
        results[LocalBackend.TRANSFORMERS] = False
    
    return results


def recommend_backend(model: str, prefer_gpu: bool = True) -> LocalBackend:
    """Recommend best backend for a model"""
    # Check what's available
    import asyncio
    available = asyncio.run(detect_available_backends())
    
    # Priority order
    if prefer_gpu:
        if available.get(LocalBackend.VLLM):
            return LocalBackend.VLLM
        if available.get(LocalBackend.LLAMA_CPP):
            return LocalBackend.LLAMA_CPP
    if available.get(LocalBackend.OLLAMA):
        return LocalBackend.OLLAMA
    if available.get(LocalBackend.TRANSFORMERS):
        return LocalBackend.TRANSFORMERS
    if available.get(LocalBackend.LLAMA_CPP):
        return LocalBackend.LLAMA_CPP
    
    return LocalBackend.OLLAMA  # Default fallback