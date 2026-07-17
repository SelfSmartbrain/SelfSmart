"""Feedback endpoint — migrated from web_server.py."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.api.deps.legacy_auth import get_current_user
from src.api.services import chat_runtime
from src.config.logging import get_logger
from src.config.settings import get_settings
from src.utils.auth import TokenData

router = APIRouter(prefix="/api", tags=["Feedback"])
logger = get_logger(__name__)
settings = get_settings()


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_index: int
    is_positive: bool
    comment: Optional[str] = None


@router.post("/feedback")
async def save_feedback(
    request: FeedbackRequest, current_user: TokenData = Depends(get_current_user)
):
    feedback_path = settings.data_dir / "feedback.jsonl"
    feedback_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "conversation_id": request.conversation_id,
        "message_index": request.message_index,
        "is_positive": request.is_positive,
        "comment": request.comment,
        "user_id": current_user.user_id,
    }

    try:
        with open(feedback_path, "a") as f:
            f.write(json.dumps(feedback_data) + "\n")
        logger.info("feedback_saved", conversation_id=request.conversation_id)
        return {"status": "success"}
    except Exception as e:
        logger.error("feedback_save_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save feedback")
