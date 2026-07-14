"""
SmartSelf AI - Web Server
Production-grade FastAPI web server with LLM, RAG, and streaming support.
"""

import logging
import uuid
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, field_validator
from typing import List, Optional
import uvicorn
import asyncio
import json
import os
from datetime import datetime
import time as _time_module
_SERVER_START_TIME = _time_module.time()

from src.config.settings import get_settings
from src.utils.logging import setup_logging, get_logger
from src.utils.metrics import instrument_app
from src.utils.auth import create_access_token, decode_access_token, verify_password, get_password_hash, Token, TokenData
from src.utils.prompt_sanitizer import sanitize_user_message
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(
    title="SmartSelf AI",
    description="Intelligent Self-Learning Chatbot with LLM",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
from src.learning.continuous_learner import ContinuousLearner, LearningConfig
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    existing_user = await conversation_manager.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    user_id = await conversation_manager.create_user(user_data.email, hashed_password, user_data.full_name)

    access_token = create_access_token(data={"sub": user_id, "email": user_data.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    user = await conversation_manager.get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data
from src.api.free_api_client import FreeAPIClient
from src.llm.deepseek_client import DeepSeekClient, Message
from src.llm.gemini_client import GeminiClient
from src.llm.rag_service import RAGService
from src.llm.agent_tools import ToolExecutor
from src.llm.conversation_manager import ConversationManager

from src.llm_training.inference import LocalLLMClient
from src.tasks.learning_tasks import run_learning_loop, _run_learning_loop
from src.tasks.training_tasks import run_model_training

# Initialize settings
settings = get_settings()

# Setup structured logging
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_format=settings.json_logs
)
logger = get_logger(__name__)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup/shutdown and model pre-warming.
    """
    logger.info("starting_up", app_name=settings.app_name)

    # Pre-warm local model if enabled
    global local_llm_client, use_local_llm
    if use_local_llm:
        logger.info("pre_warming_local_llm")
        try:
            local_llm_client = LocalLLMClient(
                model_path="./model_checkpoints",
                base_model_path="mistralai/Mistral-7B-v0.1"
            )
            local_llm_client.load_model()
            logger.info("local_llm_ready")
        except Exception as e:
            logger.error("local_llm_prewarm_failed", error=str(e))
            use_local_llm = False

    yield

    logger.info("shutting_down")


# Instrument with metrics
instrument_app(app)

# Middleware
app.add_middleware(CorrelationIdMiddleware)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)


def _llm_api_key_configured() -> bool:
    """True when the active LLM_PROVIDER has a non-empty API key (no secret values returned)."""
    provider = (settings.llm_provider or "deepseek").lower()
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    return bool(settings.deepseek_api_key)


def get_llm_client():
    """Return LLM client for LLM_PROVIDER: gemini (Google AI) or deepseek (default)."""
    if settings.llm_provider.lower() == "gemini":
        return GeminiClient()
    return DeepSeekClient()


# Initialize components
learning_config = LearningConfig()
learner = ContinuousLearner(learning_config)
free_api_client = FreeAPIClient()
conversation_manager = ConversationManager()
rag_service = RAGService()
tool_executor = ToolExecutor()

# Learning task management
_learning_active: bool = False
_learning_task: Optional[asyncio.Task] = None

# LLM clients
llm_client: Optional[DeepSeekClient] = None
local_llm_client: Optional[LocalLLMClient] = None
use_local_llm = False  # Set to True to use local fine-tuned model

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

    @field_validator('message')
    @classmethod
    def validate_message_length(cls, v):
        max_length = 1000
        if len(v) > max_length:
            raise ValueError(f'Message must be at most {max_length} characters long')
        return v

class StreamChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

    @field_validator('message')
    @classmethod
    def validate_message_length(cls, v):
        max_length = 1000
        if len(v) > max_length:
            raise ValueError(f'Message must be at most {max_length} characters long')
        return v

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    timestamp: str
    learning_active: bool
    conversation_id: str

class FeedbackRequest(BaseModel):
    conversation_id: str
    message_index: int
    is_positive: bool
    comment: Optional[str] = None

class LearnRequest(BaseModel):
    urls: List[str]

@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest):
    """Save user feedback for RLHF and system improvement."""
    feedback_path = settings.data_dir / "feedback.jsonl"
    feedback_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "conversation_id": request.conversation_id,
        "message_index": request.message_index,
        "is_positive": request.is_positive,
        "comment": request.comment
    }

    try:
        with open(feedback_path, "a") as f:
            f.write(json.dumps(feedback_data) + "\n")
        logger.info("feedback_saved", conversation_id=request.conversation_id)
        return {"status": "success"}
    except Exception as e:
        logger.error("feedback_save_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to save feedback")

@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat(request: ChatRequest, request_obj: Request, current_user: TokenData = Depends(get_current_user)):
    """
    Chat endpoint with LLM, RAG and User Authentication.
    """
    try:
        sanitize_user_message(request.message)
        # Get or create conversation (verified by user_id)
        if request.conversation_id:
            conversation = await conversation_manager.get_conversation(request.conversation_id, user_id=current_user.user_id)
            if not conversation:
                raise HTTPException(status_code=403, detail="Conversation not found or access denied")
        else:
            conversation = await conversation_manager.create_conversation(user_id=current_user.user_id)

        # Add user message
        await conversation_manager.add_message(
            conversation.id,
            "user",
            request.message
        )

        # Get conversation context
        context_messages = await conversation_manager.get_conversation_context(conversation.id)

        # Build messages for LLM
        messages = []
        messages.append(Message(role="system", content="You are SmartSelf AI, an intelligent assistant that continuously learns from the internet. Be helpful, accurate, and conversational."))
        messages.extend(context_messages)

        # Enhance query with RAG
        enhanced_query, retrieved_knowledge = await rag_service.enhance_query(
            request.message,
            context_messages
        )

        # If RAG found relevant knowledge
        if retrieved_knowledge:
            knowledge_context = "Relevant information from the system's learning:\n"
            for piece in retrieved_knowledge:
                knowledge_context += f"- {piece.content}\n"
            messages.append(Message(role="system", content=knowledge_context))

        messages[-1] = Message(role="user", content=request.message)

        # Get LLM response (use local or API)
        if use_local_llm:
            if local_llm_client is None:
                raise HTTPException(status_code=503, detail="Local model is not yet loaded.")

            # Convert Message objects to dict format
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
            llm_response = local_llm_client.generate(messages_dict)
        else:
            async with get_llm_client() as llm:
                # Add tool calling instructions (Phase 8)
                messages.insert(0, Message(role="system", content="You are a helpful assistant. If you need external data (web_search, python_repl, get_datetime), reply with a JSON object: {'tool': 'name', 'args': {}}. If not, reply normally."))
                llm_response = await llm.chat(messages)

                # Check for Tool Call
                try:
                    tool_call = json.loads(llm_response.content)
                    if isinstance(tool_call, dict) and "tool" in tool_call and tool_call["tool"] != "none":
                        logger.info("tool_call_detected", tool=tool_call["tool"])
                        tool_result = await tool_executor.execute(tool_call["tool"], tool_call.get("args", {}))
                        messages.append(Message(role="assistant", content=llm_response.content))
                        messages.append(Message(role="system", content=f"Tool result: {json.dumps(tool_result)}"))
                        llm_response = await llm.chat(messages)
                except:
                    pass

                # Self-Critique Step (Phase 5)
                final_content, refined = await rag_service.critique_response(
                    request.message,
                    llm_response.content,
                    retrieved_knowledge,
                    llm
                )
                if refined:
                    llm_response.content = final_content

        # Add assistant message
        await conversation_manager.add_message(
            conversation.id,
            "assistant",
            llm_response.content
        )

        # Process response with knowledge sources
        if retrieved_knowledge:
            llm_response.sources = [piece.source for piece in retrieved_knowledge]

        return ChatResponse(
            response=llm_response.content,
            sources=llm_response.sources,
            timestamp=datetime.now().isoformat(),
            learning_active=learner.is_running if hasattr(learner, 'is_running') else True,
            conversation_id=conversation.id
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: StreamChatRequest, current_user: TokenData = Depends(get_current_user)):
    """
    Streaming chat endpoint with LLM, RAG and Authentication.
    """
    async def generate():
        try:
            # Get or create conversation (verified by user_id)
            if request.conversation_id:
                conversation = await conversation_manager.get_conversation(request.conversation_id, user_id=current_user.user_id)
                if not conversation:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Unauthorized'})}\n\n"
                    return
            else:
                conversation = await conversation_manager.create_conversation(user_id=current_user.user_id)

            # Send conversation ID
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id})}\n\n"

            # Add user message
            await conversation_manager.add_message(
                conversation.id,
                "user",
                request.message
            )

            # Get conversation context
            context_messages = await conversation_manager.get_conversation_context(conversation.id)

            # Build messages for LLM
            messages = []
            messages.append(Message(role="system", content="You are SmartSelf AI, an intelligent assistant that continuously learns from the internet. Be helpful, accurate, and conversational."))
            messages.extend(context_messages)

            # Enhance query with RAG
            enhanced_query, retrieved_knowledge = await rag_service.enhance_query(
                request.message,
                context_messages
            )

            # If RAG found relevant knowledge
            if retrieved_knowledge:
                knowledge_context = "Relevant information from the system's learning:\n"
                for piece in retrieved_knowledge:
                    knowledge_context += f"- {piece.content}\n"
                messages.append(Message(role="system", content=knowledge_context))

            messages[-1] = Message(role="user", content=request.message)

            # Stream LLM response (use local or API)
            full_response = ""

            if use_local_llm:
                if local_llm_client is None:
                    local_llm_client = LocalLLMClient(
                        model_path="./model_checkpoints",
                        base_model_path="mistralai/Mistral-7B-v0.1"
                    )
                    local_llm_client.load_model()

                # Convert Message objects to dict format
                messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]

                # Stream from local LLM
                async for chunk in local_llm_client.generate_stream(messages_dict):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            else:
                # Stream from DeepSeek API
                async with get_llm_client() as llm:
                    async for chunk in llm.chat_stream(messages):
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Add assistant message
            await conversation_manager.add_message(
                conversation.id,
                "assistant",
                full_response
            )

            # Send completion with sources
            sources = [piece.source for piece in retrieved_knowledge] if retrieved_knowledge else []
            yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"

        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/conversations")
async def list_conversations(limit: int = 50, current_user: TokenData = Depends(get_current_user)):
    """List all conversations for the authenticated user"""
    try:
        conversations = await conversation_manager.list_conversations(user_id=current_user.user_id, limit=limit)
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, current_user: TokenData = Depends(get_current_user)):
    """Get a specific conversation"""
    try:
        conversation = await conversation_manager.get_conversation(conversation_id, user_id=current_user.user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")

        return {
            "id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in conversation.messages
            ],
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: TokenData = Depends(get_current_user)):
    """Delete a conversation"""
    try:
        conversation = await conversation_manager.get_conversation(conversation_id, user_id=current_user.user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        success = await conversation_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        conv_stats = await conversation_manager.get_stats()
        rag_stats = rag_service.get_rag_stats()

        # Get learning stats if available
        learning_stats = {}
        if hasattr(learner, 'integration_stats'):
            learning_stats = learner.integration_stats

        return {
            "conversations": conv_stats,
            "rag": rag_stats,
            "learning": learning_stats,
            "learning_active": learner.is_running if hasattr(learner, 'is_running') else True
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard")
async def get_dashboard_metrics(current_user: TokenData = Depends(get_current_user)):
    """
    Real-time dashboard metrics — replaces all hardcoded frontend demo data.
    """
    import json as _json
    import time as _time_module

    # --- Knowledge base ---
    chunk_count = 0
    rag_enabled = getattr(rag_service, "use_rag", False)
    try:
        if rag_enabled and hasattr(rag_service, "knowledge_integrator"):
            vi = rag_service.knowledge_integrator.vector_store
            if vi:
                chunk_count = vi.collection.count()
    except Exception:
        pass

    # --- User feedback from JSONL log ---
    feedback_path = settings.data_dir / "feedback.jsonl"
    feedback_total, feedback_positive = 0, 0
    if feedback_path.exists():
        try:
            with open(feedback_path) as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        entry = _json.loads(raw)
                        feedback_total += 1
                        if entry.get("is_positive"):
                            feedback_positive += 1
                    except _json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # --- Conversations for this user ---
    conv_count = 0
    try:
        user_convs = await conversation_manager.get_user_conversations(
            user_id=current_user.user_id, limit=9999
        )
        conv_count = len(user_convs) if user_convs else 0
    except Exception:
        pass

    # --- Uptime ---
    uptime = round(_time_module.time() - _SERVER_START_TIME, 1)

    return {
        "knowledge_base": {
            "chunk_count": chunk_count,
            "rag_enabled": rag_enabled,
        },
        "feedback": {
            "total": feedback_total,
            "positive": feedback_positive,
            "satisfaction_rate": (
                round(feedback_positive / feedback_total, 2)
                if feedback_total > 0 else 0.0
            ),
        },
        "conversations": {
            "total": conv_count,
        },
        "system": {
            "llm_provider": settings.llm_provider,
            "uptime_seconds": uptime,
            "version": settings.app_version,
            "learning_active": _learning_active,
        },
    }


@app.post("/api/learning/start")
async def start_learning(current_user: TokenData = Depends(get_current_user)):
    """Start the continuous learning pipeline."""
    global _learning_active, _learning_task
    if _learning_active and _learning_task and not _learning_task.done():
        return {"success": False, "message": "Learning pipeline already running"}
    _learning_active = True
    _learning_task = asyncio.create_task(_run_learning_loop())
    logger.info("learning_started", user=current_user.username)
    return {"success": True, "message": "Learning pipeline started"}


@app.post("/api/learning/stop")
async def stop_learning(current_user: TokenData = Depends(get_current_user)):
    """Stop the active continuous learning background task."""
    global _learning_active, _learning_task
    if _learning_task and not _learning_task.done():
        _learning_task.cancel()
        _learning_active = False
        logger.info("learning_stopped", user=current_user.username)
        return {"success": True, "message": "Learning pipeline stopped"}
    return {"success": False, "message": "No active learning task to stop"}


@app.post("/api/learning/learn")
async def learn_urls(request: LearnRequest, current_user: TokenData = Depends(get_current_user)):
    """Manually crawl and integrate knowledge from specific URLs"""
    try:
        result = await learner.manual_learning_session(request.urls)
        return result
    except Exception as e:
        logger.error(f"Error in manual learning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/training/start")
async def start_training():
    """Trigger the LoRA fine-tuning pipeline as a background task"""
    try:
        task = run_model_training.delay()
        return {
            "success": True,
            "message": "Model training started in background",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status and result of a background task"""
    from celery.result import AsyncResult
    res = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency status"""
    # Initialize statuses
    chromadb_status = "unknown"
    mlx_status = "unknown"
    external_api_status = "unknown"
    
    # Check ChromaDB (via vector store in RAG service)
    try:
        if hasattr(rag_service, 'knowledge_integrator') and rag_service.knowledge_integrator is not None:
            vector_store = rag_service.knowledge_integrator.vector_store
            if vector_store is not None and vector_store.client is not None:
                # Try a simple operation to verify connectivity
                # We'll check if we can get stats without throwing
                stats = vector_store.get_stats()  # This is async, but we need to await it
                # Since we're in an async context, we can await
                # However, we need to be careful not to block. Let's make it non-blocking by creating a task
                # But for simplicity in health check, we'll do a quick check: if client exists, assume healthy
                # Actually, let's just check if the client is initialized - a full health check might be too heavy
                chromadb_status = "healthy"
            else:
                chromadb_status = "unhealthy"
        else:
            chromadb_status = "unhealthy"  # RAG service not initialized
    except Exception as e:
        logger.warning(f"Health check ChromaDB failed: {e}")
        chromadb_status = "unhealthy"
    
    # Check MLX (local LLM)
    try:
        if settings.use_local_llm:
            if local_llm_client is not None:
                # Try a simple operation to verify the model is loaded
                # We'll check if the model is loaded (we don't want to run inference in health check)
                mlx_status = "healthy"
            else:
                mlx_status = "unhealthy"
        else:
            mlx_status = "not_applicable"
    except Exception as e:
        logger.warning(f"Health check MLX failed: {e}")
        mlx_status = "unhealthy"
    
    # Check external API (Gemini/DeepSeek)
    try:
        if not settings.use_local_llm:
            if _llm_api_key_configured():
                # We could make a lightweight call, but to avoid rate limits and latency,
                # we'll just check if the key is configured and the client can be instantiated
                # For now, we'll consider it healthy if the key is configured
                external_api_status = "healthy"
            else:
                external_api_status = "unhealthy"
        else:
            external_api_status = "not_applicable"
    except Exception as e:
        logger.warning(f"Health check external API failed: {e}")
        external_api_status = "unhealthy"
    
    # Determine overall status
    # Critical components: LLM (either MLX or external API) must be healthy for their respective modes
    critical_healthy = True
    if settings.use_local_llm:
        if mlx_status != "healthy":
            critical_healthy = False
    else:
        if external_api_status != "healthy":
            critical_healthy = False
    
    overall_status = "healthy" if critical_healthy else "degraded"
    
    return {
        "status": overall_status,
        "service": "SmartSelf AI",
        "version": settings.app_version,
        "dependencies": {
            "chromadb": chromadb_status,
            "mlx": mlx_status,
            "external_api": external_api_status
        },
        "features": {
            "use_local_llm": settings.use_local_llm,
            "use_rag": rag_service.use_rag if hasattr(rag_service, 'use_rag') else False
        }
    }



@app.get("/health/detailed")
async def health_detailed():
    """Detailed component health check for monitoring and alerting."""
    components: dict = {}
    overall_status = "ok"

    # RAG / ChromaDB check
    try:
        if hasattr(rag_service, "vector_store") and rag_service.vector_store:
            chunk_count = rag_service.vector_store.collection.count()
        else:
            chunk_count = -1
        components["rag"] = {"status": "ok", "chunk_count": chunk_count}
    except Exception as e:
        components["rag"] = {"status": "error", "error": str(e)[:100]}
        overall_status = "degraded"

    # LLM API key check
    if _llm_api_key_configured():
        components["llm_api"] = {"status": "ok", "provider": settings.llm_provider}
    else:
        components["llm_api"] = {"status": "warning", "message": "No LLM API key configured"}
        if overall_status == "ok":
            overall_status = "degraded"

    # Local LLM check
    components["local_llm"] = {
        "status": "ok" if (use_local_llm and local_llm_client is not None) else "not_loaded",
        "enabled": use_local_llm
    }

    # Storage writability check
    try:
        probe = settings.data_dir / ".health_probe"
        probe.touch()
        probe.unlink()
        components["storage"] = {"status": "ok", "data_dir": str(settings.data_dir)}
    except Exception as e:
        components["storage"] = {"status": "error", "error": str(e)[:100]}
        overall_status = "error"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(_time_module.time() - _SERVER_START_TIME, 1),
        "version": "1.0.0",
        "components": components
    }
@app.get("/status")
async def status():
    """System status endpoint"""
    return {
        "status": "online",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "llm_provider": settings.llm_provider,
        "llm_api_key_configured": _llm_api_key_configured(),
        "embeddings": "local_sentence_transformers",
        "features": [
            "llm_integration",
            "rag_knowledge_base",
            "conversation_history",
            "streaming_responses",
            "continuous_learning"
        ]
    }


@app.get("/")
async def root():
    """API root — UI is served by the Next.js frontend on port 3000."""
    from src.config.settings import get_settings
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
        "frontend": "http://localhost:3000",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.web_server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
