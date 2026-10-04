import asyncio
import logging
from procrastinate import App, AiopgConnector

from app.config.settings import settings
from app.db.base import async_session_maker
from app.models.document import Document
from app.repositories.chunk import DocumentChunkRepository
from app.services.chunking import chunk_text
from app.services.embeddings import EmbeddingService
from app.services.pdf_text import extract_pdf_text
from app.services.storage import StorageService
import tempfile
import os

logger = logging.getLogger(__name__)

# Re-use the existing async database URL for procrastinate
connector = AiopgConnector(dsn=settings.database_url.replace("+asyncpg", ""))
app = App(connector=connector)

@app.task
async def process_document_task(document_id: int):
    """Background task to extract, chunk, and embed a document."""
    async with async_session_maker() as session:
        document = await session.get(Document, document_id)
        if not document:
            return

        storage = StorageService()
        embeddings = EmbeddingService()
        chunks_repo = DocumentChunkRepository(session)

        try:
            # Download from S3
            key = f"{document.owner_id}/{document.storage_filename}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                storage.download_fileobj(key, tmp)
                tmp_path = tmp.name

            # Extract markdown
            extracted_text = extract_pdf_text(tmp_path)
            os.unlink(tmp_path)

            document.extracted_text = extracted_text
            
            # Chunk and Embed
            contents = chunk_text(extracted_text)
            if contents:
                embedded_vectors = [embeddings.embed(content) for content in contents]
                await chunks_repo.create_for_document(
                    document_id=document.id,
                    contents=contents,
                    embeddings=embedded_vectors,
                )

            document.status = "ready"
            await session.commit()
            logger.info(f"Successfully processed document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            document.status = "failed"
            document.error_message = str(e)
            await session.commit()
            raise

