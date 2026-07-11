import re
import os
import uuid
import asyncio
import logging
from typing import AsyncGenerator, List, Dict, Any, Tuple, Optional
from app.core.config import settings
from app.core.exceptions import EntityNotFoundError
from app.domain.interfaces.repositories import IChatRepository, IDocumentRepository, IVectorRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(
        self,
        chat_repo: IChatRepository,
        doc_repo: IDocumentRepository,
        vector_repo: IVectorRepository,
        embedding_service: EmbeddingService
    ):
        self.chat_repo = chat_repo
        self.doc_repo = doc_repo
        self.vector_repo = vector_repo
        self.embedding_service = embedding_service
        self.gemini_configured = bool(settings.GEMINI_API_KEY)
        self.cohere_configured = bool(settings.COHERE_API_KEY)

        if self.gemini_configured:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    generation_config={"temperature": 0.0}
                )
                logger.info("Gemini LLM engine configured successfully for RAG.")
            except ImportError:
                self.gemini_configured = False
                logger.warning("google-generativeai package missing. Falling back to offline RAG mode.")

    async def generate_response(
        self, session_id: uuid.UUID, user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        Coordinates the RAG search-then-generate pipeline.
        Yields chunks of text as Server-Sent Events (SSE).
        Saves the final response and extracted citations to the database.
        """
        # Verify session exists
        session = await self.chat_repo.get_session(session_id)
        if not session:
            raise EntityNotFoundError(f"Chat session {session_id} not found")

        # 1. Retrieve relevant chunks from Vector DB
        logger.info(f"RAG: Generating query embedding for query: '{user_message}'")
        query_vector = await self.embedding_service.get_embedding(user_message)
        
        logger.info("RAG: Performing similarity search in Qdrant")
        raw_chunks = await self.vector_repo.similarity_search(query_vector, limit=12)
        
        # 2. Re-rank retrieved chunks
        reranked_chunks = await self._rerank_chunks(user_message, raw_chunks, limit=5)
        
        # If no context found, RAG behaves in zero-context mode
        context_str = ""
        if reranked_chunks:
            context_pieces = []
            for chunk in reranked_chunks:
                doc_id = chunk["document_id"]
                page_num = chunk.get("metadata", {}).get("page_number")
                content = chunk["content"]
                context_pieces.append(
                    f"[DocID: {doc_id}, Page: {page_num}]\n{content}"
                )
            context_str = "\n---\n".join(context_pieces)

        # 3. Call LLM (Gemini) or use offline Mock generator
        full_assistant_response = ""
        
        if self.gemini_configured:
            prompt = self._build_prompt(user_message, context_str)
            logger.info("RAG: Calling Gemini stream API")
            try:
                # Run sync generator inside thread executor to prevent blocking async loop
                loop = asyncio.get_event_loop()
                response_stream = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt, stream=True)
                )
                
                for chunk in response_stream:
                    text_piece = chunk.text
                    full_assistant_response += text_piece
                    # Yield incremental text tokens as SSE data packets
                    yield f"data: {text_piece}\n\n"
                    if not os.environ.get("PYTEST_CURRENT_TEST"):
                        await asyncio.sleep(0.01) # Yield control
            except Exception as e:
                logger.error(f"Gemini generation failed: {e}. Falling back to offline fallback.")
                self.gemini_configured = False # Trigger fallback

        # Offline Mock Fallback Mode
        if not self.gemini_configured:
            logger.info("RAG: Operating in OFFLINE Mock generation mode")
            mock_stream = self._generate_mock_stream(user_message, reranked_chunks)
            async for text_piece in mock_stream:
                full_assistant_response += text_piece
                yield f"data: {text_piece}\n\n"
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    await asyncio.sleep(0.05) # Simulate word typing delay

        # 4. Post-processing: Parse Citations and Write to database
        # Save user message to Postgres
        user_msg_db = await self.chat_repo.create_message(session_id, "USER", user_message)
        
        # Parse citations from text
        parsed_clean_response, citations = await self._parse_citations(full_assistant_response, reranked_chunks)
        
        # Save assistant message to Postgres
        assistant_msg_db = await self.chat_repo.create_message(session_id, "ASSISTANT", parsed_clean_response)
        
        # Save citation records
        citations_response = []
        for doc_id, chunk_id, snippet, page_num in citations:
            cit_db = await self.chat_repo.create_citation(
                message_id=assistant_msg_db.id,
                document_id=doc_id,
                chunk_id=str(chunk_id),
                snippet=snippet,
                page_number=page_num
            )
            citations_response.append(cit_db.model_dump(mode="json"))
            
        # Send final control packet with database metadata (citations list and message IDs)
        import json
        metadata_packet = {
            "message_id": str(assistant_msg_db.id),
            "user_message_id": str(user_msg_db.id),
            "citations": citations_response
        }
        yield f"data: [METADATA]{json.dumps(metadata_packet)}\n\n"

    async def _rerank_chunks(self, query: str, chunks: List[dict], limit: int) -> List[dict]:
        """
        Uses Cohere Rerank if configured, otherwise falls back to Qdrant's cosine scores.
        """
        if not chunks:
            return []

        if self.cohere_configured:
            try:
                import cohere
                co = cohere.Client(api_key=settings.COHERE_API_KEY)
                documents = [c["content"] for c in chunks]
                response = co.rerank(
                    query=query,
                    documents=documents,
                    top_n=limit,
                    model="rerank-english-v3.0"
                )
                
                reranked = []
                for result in response.results:
                    idx = result.index
                    chunk = chunks[idx]
                    chunk["rerank_score"] = result.relevance_score
                    reranked.append(chunk)
                return reranked
            except Exception as e:
                logger.error(f"Cohere rerank failed: {e}. Falling back to default scoring.")
                
        # Default fallback: return top K chunks sorted by Qdrant similarity score
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)
        return sorted_chunks[:limit]

    def _build_prompt(self, query: str, context: str) -> str:
        return f"""You are an Enterprise AI Support Assistant. Answer the user's question using ONLY the provided document context slices. 

If the context does not contain the answer, say exactly: "I cannot find the answer in the corporate documentation." Do not use external knowledge.

For EVERY factual statement you make, if it is derived from a context slice, you MUST append a citation referencing the DocID and Page number in square brackets exactly like: [DocID:page_number]
For example: "The corporate travel budget covers $50 per day for meals [307ecffd-50f5-42f1-8d29-4b80c50abd45:2]."
If page number is None, print None, for example: [307ecffd-50f5-42f1-8d29-4b80c50abd45:None]

Context Slices:
---
{context}
---

User Query:
{query}
"""

    async def _generate_mock_stream(
        self, query: str, chunks: List[dict]
    ) -> AsyncGenerator[str, None]:
        """
        Generates a simulated typing stream for offline development.
        """
        if not chunks:
            yield "I cannot find the answer in the corporate documentation."
            return

        # Use the first chunk to draft a simulated answered RAG sentence
        top_chunk = chunks[0]
        doc_id = top_chunk["document_id"]
        page_num = top_chunk.get("metadata", {}).get("page_number")
        filename = top_chunk.get("metadata", {}).get("filename", "document")
        content_snippet = top_chunk["content"][:200]
        
        sentences = [
            f"Based on the corporate document '{filename}', ",
            f"here is what I found regarding your search:\n\n",
            f"\"{content_snippet}...\" ",
            f"[{doc_id}:{page_num}]."
        ]
        
        for sentence in sentences:
            words = sentence.split(" ")
            for w in words:
                yield w + " "
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    await asyncio.sleep(0.01)

    async def _parse_citations(
        self, response_text: str, chunks: List[dict]
    ) -> Tuple[str, List[Tuple[uuid.UUID, uuid.UUID, str, Optional[int]]]]:
        """
        Parses raw text citations like [uuid:page_number], converts them to clean numbering like [1],
        and returns the clean text and a list of citation db mappings.
        """
        # Regex to find UUID:page_number matches
        # Matches: [307ecffd-50f5-42f1-8d29-4b80c50abd45:2] or [307ecffd-50f5-42f1-8d29-4b80c50abd45:None]
        pattern = r"\[([a-f0-9\-]{36}):(None|[0-9]+)\]"
        matches = re.findall(pattern, response_text)
        
        citations = []
        clean_text = response_text
        
        # Build document chunks mapping for lookup
        chunk_map = {str(c["document_id"]): c for c in chunks}
        
        # Track unique documents seen to replace with numbering like [1], [2]
        unique_citations = {}
        citation_counter = 1
        
        for doc_id_str, page_str in matches:
            try:
                doc_id = uuid.UUID(doc_id_str)
                page_num = int(page_str) if page_str != "None" else None
            except ValueError:
                continue

            # Resolve chunk snippet details
            chunk = chunk_map.get(doc_id_str)
            snippet = chunk["content"] if chunk else "No snippet available."
            chunk_id = uuid.UUID(chunk["chunk_id"]) if chunk else uuid.uuid4()
            
            citations.append((doc_id, chunk_id, snippet, page_num))
            
            # Map tag in text to user friendly numbering
            raw_tag = f"[{doc_id_str}:{page_str}]"
            if raw_tag not in unique_citations:
                unique_citations[raw_tag] = f"[{citation_counter}]"
                citation_counter += 1
                
            clean_text = clean_text.replace(raw_tag, unique_citations[raw_tag])
            
        return clean_text, citations
