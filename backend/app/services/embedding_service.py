import hashlib
import logging
from typing import List
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.cohere_client = None
        self.gemini_configured = False

        if settings.COHERE_API_KEY:
            try:
                import cohere
                self.cohere_client = cohere.Client(api_key=settings.COHERE_API_KEY)
                logger.info("Cohere embedding client initialized successfully.")
            except ImportError:
                logger.warning("Cohere package not installed, unable to use Cohere embeddings.")

        if settings.GEMINI_API_KEY and not self.cohere_client:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_configured = True
                logger.info("Gemini embedding client configured successfully.")
            except ImportError:
                logger.warning("google-generativeai package not installed, unable to use Gemini embeddings.")

        if not self.cohere_client and not self.gemini_configured:
            logger.warning("No API keys found for Cohere or Gemini. Running in OFFLINE mock embedding mode.")

    async def get_embedding(self, text: str) -> List[float]:
        # Clean text
        text = text.replace("\n", " ").strip()
        
        # 1. Try Cohere
        if self.cohere_client:
            try:
                # Cohere Embed v3 call
                response = self.cohere_client.embed(
                    texts=[text],
                    model="embed-english-v3.0",
                    input_type="search_query"
                )
                return [float(x) for x in response.embeddings[0]]
            except Exception as e:
                logger.error(f"Cohere embedding generation failed: {e}. Falling back...")

        # 2. Try Gemini
        if self.gemini_configured:
            try:
                import google.generativeai as genai
                # text-embedding-004 returns 768 dimensions
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_query"
                )
                # To match standard 1536 dimension size configured in vector DB for tests or mix-use,
                # we pad it with zeros, or let it work natively.
                # Actually, Qdrant collection is created with 1536 dims.
                # If using 768 dims, Qdrant collection will be initialized to 768 dims on startup,
                # but let's make sure it matches. Let's return the embedding list.
                # If we pad, we can ensure 1536. Let's return the native list, but for local mock we do 1536.
                # Let's pad Gemini's 768 to 1536 for seamless compatibility with Cohere/OpenAI collection setups:
                vector = [float(x) for x in response["embedding"]]
                if len(vector) < 1536:
                    vector += [0.0] * (1536 - len(vector))
                return vector
            except Exception as e:
                logger.error(f"Gemini embedding generation failed: {e}. Falling back...")

        # 3. Offline Hash-based Mock fallback (for testing and offline running)
        return self._generate_dummy_embedding(text)

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        # For simplicity, we resolve them sequentially or in bulk if supported
        if self.cohere_client:
            try:
                cleaned_texts = [t.replace("\n", " ").strip() for t in texts]
                response = self.cohere_client.embed(
                    texts=cleaned_texts,
                    model="embed-english-v3.0",
                    input_type="search_document"
                )
                return [[float(x) for x in emb] for emb in response.embeddings]
            except Exception as e:
                logger.error(f"Cohere bulk embedding failed: {e}. Falling back...")

        embeddings = []
        for text in texts:
            embeddings.append(await self.get_embedding(text))
        return embeddings

    def _generate_dummy_embedding(self, text: str) -> List[float]:
        # Generates a deterministic mock embedding of size 1536 based on the text hash
        hash_object = hashlib.sha256(text.encode("utf-8"))
        hash_digest = hash_object.digest()
        
        # Build 1536 dimensions from digest bytes
        dummy_vector = []
        for i in range(1536):
            byte_index = (i * 7) % len(hash_digest)
            val = hash_digest[byte_index] / 255.0
            # Alternate sign to simulate cosine distribution around zero
            if i % 2 == 0:
                val = -val
            dummy_vector.append(val)
            
        # Normalize vector to unit length (cosine similarity ready)
        norm = sum(x*x for x in dummy_vector) ** 0.5
        if norm > 0:
            dummy_vector = [x / norm for x in dummy_vector]
            
        return dummy_vector
