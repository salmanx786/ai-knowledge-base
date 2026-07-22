from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ORMBase

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentChunk(ORMBase):
    """A contiguous slice of a document's extracted text.

    Chunks are produced once, at upload time, straight after text extraction.
    They are the stable, ordered unit that embedding (and later retrieval)
    operates on. Each chunk carries its own ``embedding`` -- a JSON array of
    floats filled in just after the chunk is created -- but the model holds it
    as opaque data: it knows nothing about which model produced the vector, its
    dimensionality, or how it will be searched.

    ``chunk_index`` is the 0-based position of the chunk within its document and
    is what ``ORDER BY`` relies on to reconstruct reading order. The
    ``(document_id, chunk_index)`` uniqueness constraint makes that ordering an
    invariant the database enforces, not merely a convention. The FK uses
    ``ON DELETE CASCADE`` so a document's chunks are removed with the document.
    """

    __tablename__ = "document_chunks"

    __table_args__ = (
        # One chunk per position per document; also the natural ordering key.
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_id_chunk_index",
        ),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        # Every read fetches a single document's chunks, so index the FK.
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        # The chunk's vector representation, stored as a JSON array of floats.
        # Nullable and independent of the text: a chunk exists as ordered text
        # first; the embedding is filled in right after creation. JSON keeps
        # this model free of any vector-store or pgvector dependency -- that is
        # deliberately out of scope. All vectors from one model share a fixed
        # length, but that invariant lives in the embedding module, not here.
        JSON,
        nullable=True,
    )

    document: Mapped["Document"] = relationship()
