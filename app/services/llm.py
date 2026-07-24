"""Google Gemini access, isolated behind one function.

This module is the only place in the app that imports the Google Gen AI SDK or
holds a Gemini client. Every other layer -- ChatService in particular -- depends
on the plain ``generate_answer(system, context, question) -> str`` surface here
and never imports ``google.genai``. This mirrors the isolation used by
``embeddings`` and ``pdf_text``: the vendor dependency lives in exactly one file,
so it can be swapped (or mocked in tests) without reaching into service logic.

Scope is deliberately narrow per the current requirement: a single synchronous
call that returns the answer text. No streaming, no chat history, no tools, no
function calling, no memory -- those are explicitly out of scope.

The API key is *not* required at import time or at startup. The client is built
lazily on the first ``generate_answer`` call; if ``GEMINI_API_KEY`` is unset the
call raises a clear ``LLMConfigurationError`` so the app boots normally and only
fails when a chat is actually requested.
"""

from functools import lru_cache

from google import genai

from app.config.settings import settings
from app.repositories.errors import LLMConfigurationError


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Return the process-wide Gemini client, building it on first use.

    The client is cheap but not free to construct (it validates config and sets
    up an HTTP session); ``lru_cache`` makes it a singleton so repeated chat
    requests reuse one client. The API key is read lazily here rather than at
    startup: if it is missing we raise a clear error instead of letting the SDK
    fail with an opaque message. The error is a domain
    ``LLMConfigurationError`` -- the API maps it to a generic 500 without
    echoing the setting name to the client, while the message still names it in
    the logs for whoever is debugging the deployment.
    """
    if not settings.gemini_api_key:
        raise LLMConfigurationError(
            "GEMINI_API_KEY is not configured; cannot generate a chat answer."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def generate_answer(*, system: str, context: str, question: str) -> str:
    """Send the RAG prompt to Gemini and return the answer text.

    ``system`` is passed as the model's ``system_instruction`` (its standing
    role); ``context`` (retrieved chunks) and ``question`` are combined into the
    single user ``contents`` message. Splitting them this way keeps the system
    instruction out of the user turn while still handing the model the retrieved
    context.

    Returns the plain answer string via ``response.text`` -- the SDK's
    aggregated text accessor -- so callers get a ``str`` and never see the
    Gemini response object. Raises ``LLMConfigurationError`` if the API key is
    unset.
    """
    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=f"Context:\n{context}\n\nUser:\n{question}",
        config=genai.types.GenerateContentConfig(system_instruction=system),
    )
    return response.text or ""
