"""PDF text extraction, using pymupdf4llm.

Upgraded to use Markdown extraction to preserve tables and layouts 
for better LLM interpretation.
"""

from pathlib import Path

import pymupdf4llm

from app.repositories.errors import TextExtractionError


def extract_pdf_text(path: Path) -> str:
    """Return the markdown text of every page in the PDF at ``path``.

    Raises ``TextExtractionError`` if the file cannot be opened or read as a
    PDF (missing, truncated, or malformed).
    """
    try:
        md_text = pymupdf4llm.to_markdown(str(path))
        return md_text
    except Exception as exc:
        raise TextExtractionError(str(path)) from exc

