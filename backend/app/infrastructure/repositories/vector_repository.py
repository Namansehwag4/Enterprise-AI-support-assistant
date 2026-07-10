import uuid
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.domain.interfaces.repositories import IVectorRepository

class VectorRepository(IVectorRepository):
    def __init__(self):
        # We initialize QdrantClient in local mode (path-based) as per Option A
        self.client = QdrantClient(path=settings.QDRANT_PATH)
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        # Determine the dimension based on the models we expect
        # 1536 is standard for OpenAI and Cohere. Let's make it configurable or default to 1536.
        dimension = 1536  # Default dimension
        
        collections = self.client.get_collections().collections
        exists = any(c.name == settings.QDRANT_COLLECTION_NAME for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )

    async def upsert_chunks(self, document_id: uuid.UUID, chunks: List[dict]) -> None:
        points = []
        for chunk in chunks:
            # chunk has: chunk_id (UUID/str), vector (list[float]), content (str), page_number (int)
            chunk_id = chunk.get("chunk_id")
            if isinstance(chunk_id, str):
                point_id = chunk_id
            else:
                point_id = str(chunk_id)
                
            points.append(
                PointStruct(
                    id=point_id,
                    vector=chunk["vector"],
                    payload={
                        "document_id": str(document_id),
                        "content": chunk["content"],
                        "metadata": {
                            "page_number": chunk.get("page_number"),
                            "filename": chunk.get("filename")
                        }
                    }
                )
            )
            
        if points:
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points
            )

    async def delete_chunks(self, document_id: uuid.UUID) -> None:
        self.client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id))
                    )
                ]
            )
        )

    async def similarity_search(
        self, query_vector: List[float], limit: int = 5
    ) -> List[dict]:
        results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit
        )
        
        search_results = []
        for hit in results:
            search_results.append({
                "chunk_id": hit.id,
                "score": hit.score,
                "document_id": hit.payload.get("document_id"),
                "content": hit.payload.get("content"),
                "metadata": hit.payload.get("metadata", {})
            })
        return search_results
