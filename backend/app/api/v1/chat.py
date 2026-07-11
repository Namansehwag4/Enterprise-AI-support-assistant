import uuid
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_current_user, get_db
from app.domain.models.chat import (
    ChatSessionResponse, ChatSessionDetailResponse, ChatSessionCreate, MessageCreate
)
from app.domain.models.user import UserInDB
from app.infrastructure.repositories.chat_repository import ChatRepository
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService

router = APIRouter()

def get_chat_repository(db = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)

def get_rag_service(db = Depends(get_db)) -> RAGService:
    chat_repo = ChatRepository(db)
    doc_repo = DocumentRepository(db)
    vector_repo = VectorRepository()
    embedding_service = EmbeddingService()
    return RAGService(chat_repo, doc_repo, vector_repo, embedding_service)

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_in: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Create a new chat conversation thread.
    """
    return await chat_repo.create_session(user_id=current_user.id, title=session_in.title)

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user: UserInDB = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    List all chat sessions owned by the current user.
    """
    return await chat_repo.list_sessions(user_id=current_user.id)

@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(
    session_id: uuid.UUID,
    current_user: UserInDB = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Retrieve details of a chat session, including complete message history and citations.
    """
    session = await chat_repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found"
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. You do not own this chat session."
        )
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    current_user: UserInDB = Depends(get_current_user),
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Delete a chat session thread.
    """
    session = await chat_repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found"
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. You do not own this chat session."
        )
    await chat_repo.delete_session(session_id)
    return None

@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    message_in: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Send a message to the assistant inside a thread.
    Streams the RAG response word-by-word as Server-Sent Events (SSE).
    """
    generator = rag_service.generate_response(session_id, message_in.content)
    return StreamingResponse(generator, media_type="text/event-stream")
