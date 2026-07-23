from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=100)


class SearchResultResponse(BaseModel):
    document_id: int
    chunk_index: int
    content: str
    score: float
