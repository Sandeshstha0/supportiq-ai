from datetime import datetime

from pydantic import BaseModel


class KnowledgeDocumentSummary(BaseModel):
    id: str
    title: str
    source: str
    filename: str | None
    created_at: datetime | None
    indexing_status: str
    legacy: bool
    chunk_count: int
    preview: str


class KnowledgeDocumentPage(BaseModel):
    items: list[KnowledgeDocumentSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class KnowledgeChunk(BaseModel):
    index: int
    text: str


class KnowledgeDocumentDetails(KnowledgeDocumentSummary):
    chunks: list[KnowledgeChunk]


class KnowledgeMutationResponse(BaseModel):
    success: bool
    document_id: str
    title: str
    source: str
    filename: str | None
    created_at: datetime
    chunks_stored: int
    indexing_status: str
    message: str
