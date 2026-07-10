import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.interfaces.repositories import IDocumentRepository
from app.domain.models.document import DocumentResponse, DocumentCreate, DocumentStatus, DocumentInDB
from app.infrastructure.db.models import Document

class DocumentRepository(IDocumentRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, doc_id: uuid.UUID) -> Optional[DocumentInDB]:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc_db = result.scalar_one_or_none()
        if doc_db:
            return DocumentInDB.model_validate(doc_db)
        return None

    async def list_all(self, user_id: Optional[uuid.UUID] = None) -> List[DocumentResponse]:
        query = select(Document)
        if user_id:
            query = query.where(Document.uploaded_by == user_id)
        result = await self.db.execute(query.order_by(Document.created_at.desc()))
        docs = result.scalars().all()
        return [DocumentResponse.model_validate(doc) for doc in docs]

    async def create(self, doc: DocumentCreate) -> DocumentResponse:
        doc_db = Document(
            filename=doc.filename,
            storage_path=doc.storage_path,
            content_type=doc.content_type,
            file_size=doc.file_size,
            uploaded_by=doc.uploaded_by,
            status=DocumentStatus.PROCESSING.value
        )
        self.db.add(doc_db)
        await self.db.commit()
        await self.db.refresh(doc_db)
        return DocumentResponse.model_validate(doc_db)

    async def update_status(
        self, doc_id: uuid.UUID, status: DocumentStatus, error_message: Optional[str] = None
    ) -> DocumentResponse:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc_db = result.scalar_one_or_none()
        if doc_db:
            doc_db.status = status.value
            if error_message is not None:
                doc_db.error_message = error_message
            await self.db.commit()
            await self.db.refresh(doc_db)
            return DocumentResponse.model_validate(doc_db)
        raise ValueError(f"Document with ID {doc_id} not found")

    async def delete(self, doc_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc_db = result.scalar_one_or_none()
        if doc_db:
            await self.db.delete(doc_db)
            await self.db.commit()
            return True
        return False
