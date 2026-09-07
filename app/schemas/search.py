from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=100)


class SearchResultResponse(BaseModel):
    document_id: int
    chunk_index: int
    content: str
    semantic_score: float
    rerank_score: float | None = None
