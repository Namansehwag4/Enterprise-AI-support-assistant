import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models.user import UserInDB, UserCreate
from app.domain.models.document import DocumentResponse, DocumentCreate, DocumentStatus, DocumentInDB
from app.domain.models.chat import ChatSessionResponse, ChatSessionDetailResponse, MessageResponse, CitationResponse

class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def create(self, user: UserCreate, hashed_password: str) -> UserInDB:
        pass

class IDocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doc_id: uuid.UUID) -> Optional[DocumentInDB]:
        pass

    @abstractmethod
    async def list_all(self, user_id: Optional[uuid.UUID] = None) -> List[DocumentResponse]:
        pass

    @abstractmethod
    async def create(self, doc: DocumentCreate) -> DocumentResponse:
        pass

    @abstractmethod
    async def update_status(
        self, doc_id: uuid.UUID, status: DocumentStatus, error_message: Optional[str] = None
    ) -> DocumentResponse:
        pass

    @abstractmethod
    async def delete(self, doc_id: uuid.UUID) -> bool:
        pass

class IChatRepository(ABC):
    @abstractmethod
    async def create_session(self, user_id: uuid.UUID, title: str) -> ChatSessionResponse:
        pass

    @abstractmethod
    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSessionDetailResponse]:
        pass

    @abstractmethod
    async def list_sessions(self, user_id: uuid.UUID) -> List[ChatSessionResponse]:
        pass

    @abstractmethod
    async def delete_session(self, session_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def create_message(
        self, session_id: uuid.UUID, sender: str, content: str
    ) -> MessageResponse:
        pass

    @abstractmethod
    async def create_citation(
        self,
        message_id: uuid.UUID,
        document_id: uuid.UUID,
        chunk_id: str,
        snippet: str,
        page_number: Optional[int] = None
    ) -> CitationResponse:
        pass

class IVectorRepository(ABC):
    @abstractmethod
    async def upsert_chunks(self, document_id: uuid.UUID, chunks: List[dict]) -> None:
        """
        Upsert a list of text chunks with their generated vectors into the vector database.
        Each chunk is represented as a dictionary with keys: 'chunk_id', 'vector', 'content', 'page_number'.
        """
        pass

    @abstractmethod
    async def delete_chunks(self, document_id: uuid.UUID) -> None:
        """
        Delete all chunks associated with a specific document ID.
        """
        pass

    @abstractmethod
    async def similarity_search(
        self, query_vector: List[float], limit: int = 5
    ) -> List[dict]:
        """
        Search for top K chunks most semantically similar to the query vector.
        """
        pass

