"""Cosine similarity over plain Python float lists.

Isolated here for the same reason as ``chunking`` and ``pdf_text``: one
function, one concern, no framework coupling. Callers depend only on
``list[float] -> float`` and can be tested without loading a model.
"""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return the cosine similarity of two equal-length vectors.

    Returns 0.0 for a zero vector rather than raising, so a chunk with an
    all-zero embedding is treated as maximally dissimilar to every query.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
