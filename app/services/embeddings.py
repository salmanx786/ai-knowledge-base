"""Embedding generation using Google Gemini.

Replaces local SentenceTransformers with Google Gemini text-embedding-004
API to eliminate PyTorch dependencies and reduce container size.
"""

from google import genai
from app.config.settings import get_settings

MODEL_NAME = "text-embedding-004"
EMBEDDING_DIM = 768

class EmbeddingService:
    def __init__(self):
        settings = get_settings()
        # Initialize client. The SDK will use GEMINI_API_KEY from environment.
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def embed(self, text: str) -> list[float]:
        """Return the embedding of ``text`` as a list of floats using Gemini."""
        response = self._client.models.embed_content(
            model=MODEL_NAME,
            contents=text,
        )
        return response.embeddings[0].values

