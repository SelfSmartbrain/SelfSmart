"""Chat and streaming endpoints — migrated from web_server.py."""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.api.deps.legacy_auth import get_current_user
from src.api.rate_limit import limiter
from src.api.services import chat_runtime
from src.config.logging import get_logger
from src.llm.deepseek_client import Message
from src.utils.auth import TokenData
from src.utils.prompt_sanitizer import sanitize_user_message

router = APIRouter(prefix="/api", tags=["Chat"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, v):
        if len(v) > 1000:
            raise ValueError("Message must be at most 1000 characters long")
        return v


class StreamChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message_length(cls, v):
        if len(v) > 1000:
            raise ValueError("Message must be at most 1000 characters long")
        return v


class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    timestamp: str
    learning_active: bool
    conversation_id: str


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: ChatRequest,
    request_obj: Request,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        sanitize_user_message(request.message)
        if request.conversation_id:
            conversation = await chat_runtime.conversation_manager.get_conversation(
                request.conversation_id, user_id=current_user.user_id
            )
            if not conversation:
                raise HTTPException(
                    status_code=403, detail="Conversation not found or access denied"
                )
        else:
            conversation = await chat_runtime.conversation_manager.create_conversation(
                user_id=current_user.user_id
            )

        await chat_runtime.conversation_manager.add_message(
            conversation.id, "user", request.message
        )
        context_messages = await chat_runtime.conversation_manager.get_conversation_context(
            conversation.id
        )

        messages = [
            Message(
                role="system",
                content=(
                    "You are SmartSelf AI, an intelligent assistant that continuously "
                    "learns from the internet. Be helpful, accurate, and conversational."
                ),
            )
        ]
        messages.extend(context_messages)

        _, retrieved_knowledge = await chat_runtime.rag_service.enhance_query(
            request.message, context_messages
        )

        if retrieved_knowledge:
            knowledge_context = "Relevant information from the system's learning:\n"
            for piece in retrieved_knowledge:
                knowledge_context += f"- {piece.content}\n"
            messages.append(Message(role="system", content=knowledge_context))

        messages[-1] = Message(role="user", content=request.message)

        if chat_runtime.use_local_llm:
            if chat_runtime.local_llm_client is None:
                raise HTTPException(status_code=503, detail="Local model is not yet loaded.")
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
            llm_response = chat_runtime.local_llm_client.generate(messages_dict)
        else:
            async with chat_runtime.get_llm_client() as llm:
                messages.insert(
                    0,
                    Message(
                        role="system",
                        content=(
                            "You are a helpful assistant. If you need external data "
                            "(web_search, python_repl, get_datetime), reply with a JSON object: "
                            "{'tool': 'name', 'args': {}}. If not, reply normally."
                        ),
                    ),
                )
                llm_response = await llm.chat(messages)

                try:
                    tool_call = json.loads(llm_response.content)
                    if (
                        isinstance(tool_call, dict)
                        and "tool" in tool_call
                        and tool_call["tool"] != "none"
                    ):
                        tool_result = await chat_runtime.tool_executor.execute(
                            tool_call["tool"], tool_call.get("args", {})
                        )
                        messages.append(Message(role="assistant", content=llm_response.content))
                        messages.append(
                            Message(role="system", content=f"Tool result: {json.dumps(tool_result)}")
                        )
                        llm_response = await llm.chat(messages)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

                final_content, refined = await chat_runtime.rag_service.critique_response(
                    request.message, llm_response.content, retrieved_knowledge, llm
                )
                if refined:
                    llm_response.content = final_content

        await chat_runtime.conversation_manager.add_message(
            conversation.id, "assistant", llm_response.content
        )

        if retrieved_knowledge:
            llm_response.sources = [piece.source for piece in retrieved_knowledge]

        return ChatResponse(
            response=llm_response.content,
            sources=llm_response.sources,
            timestamp=datetime.now().isoformat(),
            learning_active=(
                chat_runtime.learner.is_running
                if hasattr(chat_runtime.learner, "is_running")
                else True
            ),
            conversation_id=conversation.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("chat_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/chat/stream")
async def chat_stream(
    request: StreamChatRequest, current_user: TokenData = Depends(get_current_user)
):
    async def generate():
        try:
            if request.conversation_id:
                conversation = await chat_runtime.conversation_manager.get_conversation(
                    request.conversation_id, user_id=current_user.user_id
                )
                if not conversation:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Unauthorized'})}\n\n"
                    return
            else:
                conversation = await chat_runtime.conversation_manager.create_conversation(
                    user_id=current_user.user_id
                )

            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id})}\n\n"

            await chat_runtime.conversation_manager.add_message(
                conversation.id, "user", request.message
            )
            context_messages = await chat_runtime.conversation_manager.get_conversation_context(
                conversation.id
            )

            messages = [
                Message(
                    role="system",
                    content=(
                        "You are SmartSelf AI, an intelligent assistant that continuously "
                        "learns from the internet. Be helpful, accurate, and conversational."
                    ),
                )
            ]
            messages.extend(context_messages)

            _, retrieved_knowledge = await chat_runtime.rag_service.enhance_query(
                request.message, context_messages
            )

            if retrieved_knowledge:
                knowledge_context = "Relevant information from the system's learning:\n"
                for piece in retrieved_knowledge:
                    knowledge_context += f"- {piece.content}\n"
                messages.append(Message(role="system", content=knowledge_context))

            messages[-1] = Message(role="user", content=request.message)
            full_response = ""

            if chat_runtime.use_local_llm:
                if chat_runtime.local_llm_client is None:
                    from src.llm_training.inference import LocalLLMClient

                    chat_runtime.local_llm_client = LocalLLMClient(
                        model_path="./model_checkpoints",
                        base_model_path="mistralai/Mistral-7B-v0.1",
                    )
                    chat_runtime.local_llm_client.load_model()
                messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
                async for chunk in chat_runtime.local_llm_client.generate_stream(messages_dict):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            else:
                async with chat_runtime.get_llm_client() as llm:
                    async for chunk in llm.chat_stream(messages):
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            await chat_runtime.conversation_manager.add_message(
                conversation.id, "assistant", full_response
            )

            sources = [piece.source for piece in retrieved_knowledge] if retrieved_knowledge else []
            yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"
        except Exception as e:
            logger.error("stream_chat_error", error=str(e), exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': 'An internal error occurred'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
