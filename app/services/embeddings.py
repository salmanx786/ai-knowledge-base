"""Embedding generation, isolated behind one service.

This module is the only place in the app that imports ``sentence-transformers``
or loads an embedding model. Keeping the dependency here means callers depend on
a plain ``str -> list[float]`` method and can be reasoned about (and swapped for
a different backend) without pulling a model runtime into their imports -- the
same isolation pattern used by ``pdf_text`` and ``chunking``.

Scope is deliberately narrow per the current requirement: run one local model
(``all-MiniLM-L6-v2``) synchronously over a single string. No OpenAI, no vector
database, no semantic search, no batching, and no async inference -- those are
explicitly out of scope.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

# Local sentence-transformers model. Runs entirely on-device: no API calls, no
# credentials. ``all-MiniLM-L6-v2`` maps text to a fixed 384-dimensional vector.
MODEL_NAME = "all-MiniLM-L6-v2"

# The dimensionality every vector this service returns will have. It is fixed by
# MODEL_NAME; exposed as a constant so callers/tests can assert on it without
# loading the model.
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    """Load (once) and return the shared model instance.

    Loading a transformer is expensive -- it reads weights from disk and, on
    first ever use, downloads them. ``lru_cache`` makes this a process-wide
    singleton: the cost is paid on the first embedding and every later call is a
    cheap dict lookup, so constructing an ``EmbeddingService`` stays free.
    """
    return SentenceTransformer(MODEL_NAME)


class EmbeddingService:
    """Turns chunk text into a vector using a local model.

    Construction is cheap and side-effect-free: the model is loaded lazily on
    the first ``embed`` call (see ``_load_model``) and then reused, so wiring
    this service into another service costs nothing until an embedding is
    actually generated.
    """

    def embed(self, text: str) -> list[float]:
        """Return the embedding of ``text`` as a list of floats.

        Every returned vector has length ``EMBEDDING_DIM`` regardless of input
        length -- that consistency is what makes the vectors comparable later.
        ``encode`` yields a NumPy array; it is converted to a plain ``list`` so
        the result is JSON-serialisable and free of any NumPy dependency at the
        boundary.
        """
        vector = _load_model().encode(text)
        return vector.tolist()
