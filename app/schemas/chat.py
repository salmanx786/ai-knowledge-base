from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=100)
    conversation_id: int | None = Field(default=None, ge=1)


class ChatSource(BaseModel):
    """One retrieved chunk that fed the answer."""

    document_id: int
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    conversation_id: int


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class ConversationMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class ConversationDetail(BaseModel):
    id: int
    created_at: str
    updated_at: str
    messages: list[ConversationMessage]
