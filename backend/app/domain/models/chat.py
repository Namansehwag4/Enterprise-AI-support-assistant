import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class MessageSender(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"

class CitationResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    snippet: str
    page_number: Optional[int] = None

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: uuid.UUID
    sender: MessageSender
    content: str
    created_at: datetime
    citations: List[CitationResponse] = []

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: str

class ChatSessionCreate(BaseModel):
    title: str

class ChatSessionResponse(ChatSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatSessionDetailResponse(ChatSessionResponse):
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
