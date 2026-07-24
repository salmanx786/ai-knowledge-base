from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str
    limit: int = Field(default=5, ge=1, le=100)


class ChatSource(BaseModel):
    """One retrieved chunk that fed the answer.

    Kept intentionally minimal per the requirement: it identifies *which* chunk
    was used (document + index), not its text or score. It is a citation, not a
    payload.
    """

    document_id: int
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
