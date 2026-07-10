import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.interfaces.repositories import IChatRepository
from app.domain.models.chat import (
    ChatSessionResponse, ChatSessionDetailResponse, MessageResponse, CitationResponse
)
from app.infrastructure.db.models import ChatSession, Message, Citation, Document

class ChatRepository(IChatRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: uuid.UUID, title: str) -> ChatSessionResponse:
        session_db = ChatSession(
            user_id=user_id,
            title=title
        )
        self.db.add(session_db)
        await self.db.commit()
        await self.db.refresh(session_db)
        return ChatSessionResponse.model_validate(session_db)

    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSessionDetailResponse]:
        # We use selectinload to eagerly load nested relationships (messages -> citations -> document metadata)
        # We need the document metadata (like filename) to populate CitationResponse
        query = (
            select(ChatSession)
            .options(
                selectinload(ChatSession.messages)
                .selectinload(Message.citations)
                .joinedload(Citation.document)
            )
            .where(ChatSession.id == session_id)
        )
        result = await self.db.execute(query)
        session_db = result.scalar_one_or_none()
        
        if not session_db:
            return None
            
        # Map manually to ChatSessionDetailResponse to ensure citation document filenames are resolved
        messages_response = []
        for msg in session_db.messages:
            citations_response = []
            for cit in msg.citations:
                citations_response.append(
                    CitationResponse(
                        id=cit.id,
                        document_id=cit.document_id,
                        filename=cit.document.filename if cit.document else "Unknown Document",
                        snippet=cit.snippet,
                        page_number=cit.page_number
                    )
                )
            messages_response.append(
                MessageResponse(
                    id=msg.id,
                    sender=msg.sender,
                    content=msg.content,
                    created_at=msg.created_at,
                    citations=citations_response
                )
            )
            
        return ChatSessionDetailResponse(
            id=session_db.id,
            user_id=session_db.user_id,
            title=session_db.title,
            created_at=session_db.created_at,
            updated_at=session_db.updated_at,
            messages=messages_response
        )

    async def list_sessions(self, user_id: uuid.UUID) -> List[ChatSessionResponse]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = result.scalars().all()
        return [ChatSessionResponse.model_validate(s) for s in sessions]

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(ChatSession).where(ChatSession.id == session_id))
        session_db = result.scalar_one_or_none()
        if session_db:
            await self.db.delete(session_db)
            await self.db.commit()
            return True
        return False

    async def create_message(
        self, session_id: uuid.UUID, sender: str, content: str
    ) -> MessageResponse:
        message_db = Message(
            session_id=session_id,
            sender=sender,
            content=content
        )
        self.db.add(message_db)
        
        # Touch the updated_at timestamp of the chat session
        result = await self.db.execute(select(ChatSession).where(ChatSession.id == session_id))
        session_db = result.scalar_one_or_none()
        if session_db:
            session_db.updated_at = message_db.created_at
            
        await self.db.commit()
        await self.db.refresh(message_db)
        return MessageResponse.model_validate(message_db)

    async def create_citation(
        self,
        message_id: uuid.UUID,
        document_id: uuid.UUID,
        chunk_id: str,
        snippet: str,
        page_number: Optional[int] = None
    ) -> CitationResponse:
        citation_db = Citation(
            message_id=message_id,
            document_id=document_id,
            chunk_id=chunk_id,
            snippet=snippet,
            page_number=page_number
        )
        self.db.add(citation_db)
        await self.db.commit()
        await self.db.refresh(citation_db)
        
        # Resolve the document filename for validation response
        doc_result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc_db = doc_result.scalar_one_or_none()
        filename = doc_db.filename if doc_db else "Unknown Document"
        
        return CitationResponse(
            id=citation_db.id,
            document_id=citation_db.document_id,
            filename=filename,
            snippet=citation_db.snippet,
            page_number=citation_db.page_number
        )
