"""Conversation CRUD — migrated from web_server.py."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps.legacy_auth import get_current_user
from src.api.services import chat_runtime
from src.config.logging import get_logger
from src.utils.auth import TokenData

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])
logger = get_logger(__name__)


@router.get("")
async def list_conversations(limit: int = 50, current_user: TokenData = Depends(get_current_user)):
    try:
        conversations = await chat_runtime.conversation_manager.list_conversations(
            user_id=current_user.user_id, limit=limit
        )
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error("list_conversations_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str, current_user: TokenData = Depends(get_current_user)
):
    try:
        conversation = await chat_runtime.conversation_manager.get_conversation(
            conversation_id, user_id=current_user.user_id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")

        return {
            "id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in conversation.messages
            ],
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str, current_user: TokenData = Depends(get_current_user)
):
    try:
        conversation = await chat_runtime.conversation_manager.get_conversation(
            conversation_id, user_id=current_user.user_id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found or access denied")
        success = await chat_runtime.conversation_manager.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_conversation_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
