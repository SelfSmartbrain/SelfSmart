from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class StreamChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[str] = []
    timestamp: str
    learning_active: bool = False
    conversation_id: str
