"""PDF text extraction, isolated behind one function.

This is the only module in the app that imports PyMuPDF (``fitz``). Keeping the
dependency here means the service layer depends on a plain function with a
plain signature -- ``bytes | path -> str`` -- and can be reasoned about (and
swapped) without pulling the PDF engine into every caller's imports.

Scope is deliberately narrow per the current requirement: open the PDF, read
the text of every page, concatenate. No chunking, OCR, or layout analysis.
"""

from pathlib import Path

import fitz

from app.repositories.errors import TextExtractionError


def extract_pdf_text(path: Path) -> str:
    """Return the concatenated text of every page in the PDF at ``path``.

    Pages are joined with a single newline in page order. A valid PDF that
    happens to contain no extractable text (e.g. an empty document) returns an
    empty string -- that is a success, not an error.

    Raises ``TextExtractionError`` if the file cannot be opened or read as a
    PDF (missing, truncated, or malformed). The caller is responsible for
    deciding what to do with the already-saved file; this function never
    touches it beyond reading.
    """
    try:
        # ``with`` closes the document even if a page read raises midway.
        with fitz.open(path) as document:
            return "\n".join(page.get_text() for page in document)
    except Exception as exc:  # fitz raises assorted exception types
        raise TextExtractionError(str(path)) from exc
