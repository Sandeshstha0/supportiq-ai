
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

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
    *,
    document_id: str | None = None,
    filename: str | None = None,
) -> dict:
    """Split, embed, and store a document in Qdrant."""

    title = title.strip()
    source = source.strip()

    if not title:
        raise ValueError("Document title cannot be empty.")

    if not source:
        raise ValueError("Document source cannot be empty.")

    chunks = split_text(text)
    document_id = document_id or str(uuid4())
    version_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    content_hash = sha256(text.strip().encode("utf-8")).hexdigest()

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
                    "document_id": document_id,
                    "version_id": version_id,
                    "expected_chunks": len(chunks),
                    "filename": filename,
                    "document_created_at": created_at,
                    "content_sha256": content_hash,
                },
            )
        )

    try:
        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    except Exception:
        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[FieldCondition(
                    key="version_id", match=MatchValue(value=version_id),
                )]),
                wait=True,
            )
        except Exception:
            pass
        raise

    return {
        "success": True,
        "title": title,
        "source": source,
        "document_id": document_id,
        "filename": filename,
        "created_at": created_at,
        "indexing_status": "indexed",
        "chunks_stored": len(points),
        "message": "Document stored successfully in the knowledge base.",
    }


def replace_document(
    document_id: str,
    *,
    title: str,
    text: str,
    source: str,
    filename: str,
) -> dict:
    """Index a new version, then remove the prior vectors for one document."""
    title = title.strip()
    source = source.strip()
    if not title or not source:
        raise ValueError("Document title and source cannot be empty.")
    chunks = split_text(text)
    version_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    content_hash = sha256(text.strip().encode("utf-8")).hexdigest()
    create_knowledge_collection()
    client = get_qdrant_client()
    points = []
    for index, chunk in enumerate(chunks):
        points.append(PointStruct(
            id=str(uuid4()),
            vector=generate_embedding(chunk),
            payload={
                "title": title,
                "source": source,
                "chunk_index": index,
                "text": chunk,
                "document_id": document_id,
                "version_id": version_id,
                "expected_chunks": len(chunks),
                "filename": filename,
                "document_created_at": created_at,
                "content_sha256": content_hash,
            },
        ))

    try:
        client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    except Exception:
        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[FieldCondition(
                    key="version_id", match=MatchValue(value=version_id),
                )]),
                wait=True,
            )
        except Exception:
            pass
        raise
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))],
                must_not=[FieldCondition(key="version_id", match=MatchValue(value=version_id))],
            ),
            wait=True,
        )
    except Exception as exc:
        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(must=[FieldCondition(
                    key="version_id", match=MatchValue(value=version_id),
                )]),
                wait=True,
            )
        except Exception:
            pass
        raise RuntimeError("Replacement indexing completed, but old vectors could not be safely replaced.") from exc

    return {
        "success": True,
        "document_id": document_id,
        "title": title,
        "source": source,
        "filename": filename,
        "created_at": created_at,
        "chunks_stored": len(points),
        "indexing_status": "indexed",
        "message": "Document replaced and indexed successfully.",
    }
