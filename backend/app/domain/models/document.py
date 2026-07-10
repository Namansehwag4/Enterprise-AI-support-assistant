import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class DocumentStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentBase(BaseModel):
    filename: str
    content_type: str
    file_size: int

class DocumentCreate(DocumentBase):
    storage_path: str
    uploaded_by: uuid.UUID

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    status: DocumentStatus
    error_message: Optional[str] = None
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DocumentInDB(DocumentResponse):
    storage_path: str

