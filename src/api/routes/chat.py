from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.utils.auth import TokenData
from src.api.deps.legacy_auth import get_current_user
from src.config.settings import get_settings
from src.utils.prompt_sanitizer import sanitize_user_message
from src.api.services.chat_runtime import (
    conversation_manager,
    get_llm_client,
    learner,
    rag_service,
)
from src.api.schemas.chat import ChatRequest, ChatResponse, StreamChatRequest
import json
from datetime import datetime
import uuid
import structlog
import asyncio
from typing import List, Optional

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(
    request: ChatRequest, request_obj: Request, current_user: TokenData = Depends(get_current_user)
):
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
                raise HTTPException(
                    status_code=403, detail="Conversation not found or access denied"
                )

        # Add user message to conversation
        await conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,
            message_id=str(uuid.uuid4()),
        )

        # Get conversation history for context
        messages = await conversation_manager.get_conversation_messages(
            conversation_id=conversation_id, limit=10
        )

        # Prepare messages for LLM
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        # Check if we should use RAG
        use_rag = False
        if hasattr(rag_service, "use_rag"):
            use_rag = rag_service.use_rag

        # Get relevant documents if RAG is enabled
        context_documents = []
        if use_rag:
            try:
                context_documents = await rag_service.get_relevant_documents(
                    query=sanitized_message, top_k=5
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

        # Get LLM client
        llm_client = get_llm_client()

        # Generate response using LLM
        response = await llm_client.chat_completion(
            messages=formatted_messages, temperature=0.7, max_tokens=2000
        )
        response_text = response.choices[0].message.content
        sources = (
            [doc.metadata.get("source", "unknown") for doc in context_documents]
            if context_documents
            else []
        )

        # Add assistant message to conversation
        await conversation_manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            message_id=str(uuid.uuid4()),
        )

        # Prepare response
        response_data = ChatResponse(
            response=response_text,
            sources=list(set(sources)),  # Deduplicate
            timestamp=datetime.utcnow().isoformat(),
            learning_active=learner.is_active if hasattr(learner, "is_active") else False,
            conversation_id=conversation_id,
        )

        return response_data

    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: StreamChatRequest,
    request_obj: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Handle streaming chat requests."""
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
                raise HTTPException(
                    status_code=403, detail="Conversation not found or access denied"
                )

        # Add user message to conversation
        await conversation_manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_message,
            message_id=str(uuid.uuid4()),
        )

        # Get conversation history for context
        messages = await conversation_manager.get_conversation_messages(
            conversation_id=conversation_id, limit=10
        )

        # Prepare messages for LLM
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        # Check if we should use RAG
        use_rag = False
        if hasattr(rag_service, "use_rag"):
            use_rag = rag_service.use_rag

        # Get relevant documents if RAG is enabled
        context_documents = []
        if use_rag:
            try:
                context_documents = await rag_service.get_relevant_documents(
                    query=sanitized_message, top_k=5
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

        # Get LLM client
        llm_client = get_llm_client()

        # Define the async generator for streaming response
        async def generate_response():
            full_response = ""
            try:
                # Stream response from LLM
                async for chunk in llm_client.chat_stream(
                    messages=formatted_messages, temperature=0.7, max_tokens=2000
                ):
                    # Assuming chunk is a string token
                    if isinstance(chunk, str):
                        full_response += chunk
                        # Send SSE format: data: {"text": "...", "conversation_id": "..."}\n\n
                        yield f'data: {json.dumps({"text": chunk, "conversation_id": conversation_id})}\n\n'
                    elif isinstance(chunk, dict) and "text" in chunk:
                        # Handle case where chunk is a dict with text field
                        text_chunk = chunk["text"]
                        full_response += text_chunk
                        yield f'data: {json.dumps({"text": text_chunk, "conversation_id": conversation_id})}\n\n'
                    else:
                        # Fallback: convert to string
                        text_chunk = str(chunk)
                        full_response += text_chunk
                        yield f'data: {json.dumps({"text": text_chunk, "conversation_id": conversation_id})}\n\n'

                # After stream ends, add the complete response to conversation history
                await conversation_manager.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    message_id=str(uuid.uuid4()),
                )

                # Send final done signal
                yield f'data: {json.dumps({"text": "", "conversation_id": conversation_id, "done": True})}\n\n'

            except Exception as e:
                logger.error("stream_error", error=str(e), exc_info=True)
                # Send error in SSE format
                yield f'data: {json.dumps({"error": str(e)})}\n\n'

        return StreamingResponse(generate_response(), media_type="text/event-stream")

    except Exception as e:
        logger.error("chat_stream_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
