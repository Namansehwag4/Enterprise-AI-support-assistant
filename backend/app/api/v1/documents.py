import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, status, HTTPException
from app.api.dependencies import get_current_user, get_current_admin, get_db
from app.domain.models.document import DocumentResponse
from app.domain.models.user import UserInDB
from app.infrastructure.repositories.document_repository import DocumentRepository
from app.infrastructure.repositories.vector_repository import VectorRepository
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService

router = APIRouter()

def get_document_service(
    db = Depends(get_db)
) -> DocumentService:
    doc_repo = DocumentRepository(db)
    vector_repo = VectorRepository()
    embedding_service = EmbeddingService()
    return DocumentService(doc_repo, vector_repo, embedding_service)

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_admin: UserInDB = Depends(get_current_admin),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Upload a document (PDF, TXT, MD). Restricted to Admin role.
    Processes parsing and vector embedding generation asynchronously in background.
    """
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Supported formats: .pdf, .txt, .md"
        )
        
    uploads_dir = "./uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    
    unique_filename = f"{uuid.uuid4()}{ext}"
    storage_path = os.path.join(uploads_dir, unique_filename)
    
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
        with open(storage_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to disk storage: {e}"
        )
        
    # Write "PROCESSING" record to SQL DB
    doc = await doc_service.create_pending_document(
        filename=filename,
        storage_path=storage_path,
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        uploaded_by=current_admin.id
    )
    
    # Enqueue background task for parsing & embeddings
    background_tasks.add_task(
        doc_service.parse_and_embed_document,
        doc_id=doc.id,
        storage_path=storage_path,
        content_type=file.content_type or "text/plain",
        filename=filename
    )
    
    return doc

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: UserInDB = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    List all uploaded documents and their statuses.
    """
    return await doc_service.list_documents()

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    current_user: UserInDB = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Retrieve details of a single document.
    """
    return await doc_service.get_document(doc_id)

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    current_admin: UserInDB = Depends(get_current_admin),
    doc_service: DocumentService = Depends(get_document_service)
):
    """
    Delete a document from database, vector storage, and disk. Admin only.
    """
    await doc_service.delete_document(doc_id)
    return None
