"""Text chunking using LangChain.

Upgraded to use RecursiveCharacterTextSplitter with overlap
to preserve semantic meaning across chunk boundaries.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

# We target around 500 tokens. Using chunk_size ~2000 characters is a safe approximation.
# Overlap preserves context between boundaries.
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200

def chunk_text(text: str, *, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Split ``text`` into ordered chunks using LangChain text splitters."""
    if not text.strip():
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return text_splitter.split_text(text)

