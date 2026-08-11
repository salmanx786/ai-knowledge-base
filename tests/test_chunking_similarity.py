"""Unit tests for the pure RAG primitives.

``chunk_text`` and ``cosine_similarity`` are deliberately plain functions with
no I/O and nothing to mock, so they are tested directly and exhaustively here --
much cheaper and sharper than exercising them through the HTTP layer.
"""

import math

import pytest

from app.services.chunking import CHUNK_SIZE_WORDS, chunk_text
from app.services.similarity import cosine_similarity


# --------------------------------------------------------------------------- #
# chunk_text
# --------------------------------------------------------------------------- #
class TestChunkText:
    def test_empty_string_yields_no_chunks(self):
        assert chunk_text("") == []

    def test_whitespace_only_yields_no_chunks(self):
        # No words to place -> no chunks (never a single empty chunk).
        assert chunk_text("   \n\t  ") == []

    def test_fewer_words_than_chunk_size_is_one_chunk(self):
        assert chunk_text("just a few words", chunk_size_words=10) == [
            "just a few words"
        ]

    def test_exact_multiple_splits_evenly(self):
        text = " ".join(str(i) for i in range(6))  # 6 words
        assert chunk_text(text, chunk_size_words=3) == ["0 1 2", "3 4 5"]

    def test_remainder_goes_in_final_chunk(self):
        text = " ".join(str(i) for i in range(7))  # 7 words, size 3
        chunks = chunk_text(text, chunk_size_words=3)
        assert chunks == ["0 1 2", "3 4 5", "6"]

    def test_order_is_preserved_across_chunks(self):
        text = " ".join(str(i) for i in range(100))
        chunks = chunk_text(text, chunk_size_words=10)
        rejoined = " ".join(chunks)
        assert rejoined == text

    def test_internal_whitespace_is_normalized(self):
        # str.split() collapses runs of whitespace and drops leading/trailing.
        assert chunk_text("  a\t\tb\n\nc  ", chunk_size_words=10) == ["a b c"]

    def test_no_chunk_exceeds_requested_size(self):
        text = " ".join("w" for _ in range(45))
        chunks = chunk_text(text, chunk_size_words=20)
        assert [len(c.split()) for c in chunks] == [20, 20, 5]

    def test_default_chunk_size_is_within_embedding_window(self):
        # Guards the deliberate alignment with all-MiniLM-L6-v2's 256-token
        # window (~1.3 tokens/word) so it is not silently bumped back up.
        assert CHUNK_SIZE_WORDS <= 220


# --------------------------------------------------------------------------- #
# cosine_similarity
# --------------------------------------------------------------------------- #
class TestCosineSimilarity:
    def test_identical_vectors_score_one(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_score_zero(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors_score_negative_one(self):
        assert cosine_similarity([1.0, 1.0], [-1.0, -1.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero_not_error(self):
        # Guards against division by zero -- an all-zero embedding is treated as
        # maximally dissimilar rather than raising.
        assert cosine_similarity([0.0, 0.0, 0.0], [1.0, 2.0, 3.0]) == 0.0
        assert cosine_similarity([1.0, 2.0, 3.0], [0.0, 0.0, 0.0]) == 0.0

    def test_magnitude_does_not_affect_direction(self):
        # Cosine is scale-invariant: scaling a vector leaves the score unchanged.
        base = cosine_similarity([1.0, 1.0], [1.0, 0.0])
        scaled = cosine_similarity([10.0, 10.0], [5.0, 0.0])
        assert base == pytest.approx(scaled)
        assert base == pytest.approx(1.0 / math.sqrt(2))
