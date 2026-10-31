from pydantic import BaseModel, Field


class KnowledgeDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=10, max_length=50000)
    source: str = Field(default="manual", min_length=1, max_length=100)


class KnowledgeDocumentResponse(BaseModel):
    success: bool
    title: str
    source: str
    chunks_stored: int
    message: str


class KnowledgeSearchResponse(BaseModel):
    query: str
    count: int
    results: list[dict]