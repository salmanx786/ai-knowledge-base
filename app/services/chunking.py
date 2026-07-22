"""Text chunking, isolated behind one pure function.

This module is the single home of the rule for how a document's text is split
into chunks. Keeping it separate from persistence and PDF handling means the
splitting logic is a plain ``str -> list[str]`` with no database, no I/O, and
nothing to mock -- trivially testable and swappable without touching callers.

Scope is deliberately narrow per the current requirement: split on whitespace
into runs of approximately ``CHUNK_SIZE_WORDS`` words, preserving order. No
embeddings, no overlap, no sentence/semantic awareness, no tokenizer.
"""

# Approximate target size of each chunk, in whitespace-delimited words. Chunks
# are cut on word boundaries, so every chunk except the last has exactly this
# many words; the last holds the remainder.
CHUNK_SIZE_WORDS = 800


def chunk_text(text: str, *, chunk_size_words: int = CHUNK_SIZE_WORDS) -> list[str]:
    """Split ``text`` into ordered chunks of ~``chunk_size_words`` words.

    Words are separated on any whitespace (``str.split``), which also collapses
    runs of whitespace and drops leading/trailing blanks. Each chunk's words are
    rejoined with a single space, so the output normalizes internal whitespace
    but preserves word order and the sequence of chunks.

    Returns an empty list for empty or whitespace-only input -- there are no
    words to place, so there are no chunks (never a single empty chunk). By
    construction no returned chunk is ever empty.
    """
    words = text.split()
    return [
        " ".join(words[start : start + chunk_size_words])
        for start in range(0, len(words), chunk_size_words)
    ]
