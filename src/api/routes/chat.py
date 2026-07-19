from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.utils.auth import TokenData, get_current_user
from src.config.settings import get_settings
from src.utils.prompt_sanitizer import sanitize_user_message
from src.agents.conversation_manager import conversation_manager
from src.rag.rag_service import rag_service
from src.learning.continuous_learner import learner
from src.llm.local_llm import local_llm_client, use_local_llm
from src.llm.provider import get_llm_client
from src.agents.tool_executor import tool_executor
from src.api.schemas.chat import ChatRequest, ChatResponse, StreamChatRequest
import json
from datetime import datetime
import uuid
import structlog
import asyncio
from typing import List, Optional

logger = structlog.get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: ChatRequest, request_obj: Request, current_user: TokenData = Depends(get_current_user)):
    """Handle chat requests with optional RAG and tool use."""
    try:
        # Sanitize input
        sanitized_message = sanitize_user_message(request.message)
        
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = await conversation_manager.create_conversation(current_user.email)
        else:
            # Verify ownership
            conv_owner = await conversation_manager.get_conversation_owner(conversation_id)
            if conv_owner != current_user.email:
                raise HTTPException(status_code=403, detail="Conversation not found or access denied")
        
        # Add user message to conversation
        await conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,
            message_id=str(uuid.uuid4())
        )
        
        # Get conversation history for context
        messages = await conversation_manager.get_conversation_messages(
            conversation_id=conversation_id,
            limit=10
        )
        
        # Prepare messages for LLM
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Check if we should use RAG
        use_rag = False
        if hasattr(rag_service, 'use_rag'):
            use_rag = rag_service.use_rag
        
        # Get relevant documents if RAG is enabled
        context_documents = []
        if use_rag:
            try:
                context_documents = await rag_service.get_relevant_documents(
                    query=sanitized_message,
                    top_k=5
                )
            except Exception as e:
                logger.warning("rag_retrieval_failed", error=str(e))
        
        # Add context to system message if available
        if context_documents:
            context_text = "\n\n".join([doc.content for doc in context_documents])
            system_message = f"You are a helpful assistant. Use the following context to answer the user's question:\n\n{context_text}"
            # Insert or update system message
            if formatted_messages and formatted_messages[0]["role"] == "system":
                formatted_messages[0]["content"] = system_message
            else:
                formatted_messages.insert(0, {"role": "system", "content": system_message})
        
        # Get LLM response
        if use_local_llm and local_llm_client is not None:
            # Use local LLM
            llm_response = local_llm_client.generate(formatted_messages)
            response_text = llm_response
            sources = [doc.metadata.get("source", "unknown") for doc in context_documents] if context_documents else []
        else:
            # Use remote LLM
            async with get_llm_client() as llm:
                response = await llm.chat_completion(
                    messages=formatted_messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                response_text = response.choices[0].message.content
                sources = [doc.metadata.get("source", "unknown") for doc in context_documents] if context_documents else []
        
        # Add assistant message to conversation
        await conversation_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            message_id=str(uuid.uuid4())
        )
        
        # Prepare response
        response_data = ChatResponse(
            response=response_text,
            sources=list(set(sources)),  # Deduplicate
            timestamp=datetime.utcnow().isoformat(),
            learning_active=learner.is_active if hasattr(learner, 'is_active') else False,
            conversation_id=conversation_id
        )
        
        return response_data
        
    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/chat/stream")
async def chat_stream(request: StreamChatRequest, current_user: TokenData = Depends(get_current_user)):
    """Handle streaming chat requests."""
    try:
        # Similar to chat but returns streaming response
        # For brevity, we'll implement a simplified version
        # In a real implementation, this would yield tokens as they're generated
        
        # Reuse chat logic but return StreamingResponse
        # This is a placeholder - actual streaming would be more complex
        async def generate_response():
            # Simulate streaming by yielding chunks
            yield "{\"response\": \"This is a streaming response placeholder\", \"done\": true}"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain"
        )
    except Exception as e:
        logger.error("chat_stream_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
