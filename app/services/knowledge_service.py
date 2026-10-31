
from uuid import uuid4

from qdrant_client.models import PointStruct

from app.services.embedding_service import generate_embedding
from app.services.qdrant_service import (
    COLLECTION_NAME,
    create_knowledge_collection,
    get_qdrant_client,
)


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """Split a document into overlapping text chunks."""

    text = text.strip()

    if not text:
        raise ValueError("Document text cannot be empty.")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def add_document(
    title: str,
    text: str,
    source: str = "manual",
) -> dict:
    """Split, embed, and store a document in Qdrant."""

    title = title.strip()
    source = source.strip()

    if not title:
        raise ValueError("Document title cannot be empty.")

    if not source:
        raise ValueError("Document source cannot be empty.")

    chunks = split_text(text)

    # Ensure the collection exists before storing vectors.
    create_knowledge_collection()

    client = get_qdrant_client()
    points = []

    for index, chunk in enumerate(chunks):
        vector = generate_embedding(chunk)

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "title": title,
                    "source": source,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return {
        "success": True,
        "title": title,
        "source": source,
        "chunks_stored": len(points),
        "message": "Document stored successfully in the knowledge base.",
    }
