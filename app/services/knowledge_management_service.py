from hashlib import sha256

from qdrant_client.models import FieldCondition, Filter, MatchValue
from app.services.qdrant_service import COLLECTION_NAME, get_qdrant_client


def _collection_exists(client) -> bool:
    return COLLECTION_NAME in {
        collection.name for collection in client.get_collections().collections
    }


def _scroll_points(client, points_filter: Filter | None = None) -> list:
    points = []
    offset = None
    while True:
        batch, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=points_filter,
            offset=offset,
            limit=256,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(batch)
        if next_offset is None:
            break
        offset = next_offset
    return points


def _legacy_id(payload: dict) -> str:
    identity = f"{payload.get('title', 'Untitled')}\0{payload.get('source', 'unknown')}"
    return "legacy-" + sha256(identity.encode("utf-8")).hexdigest()[:24]


def _document_key(payload: dict) -> str:
    return str(payload.get("document_id") or _legacy_id(payload))


def _summarize(points: list) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    for point in points:
        payload = point.payload or {}
        key = _document_key(payload)
        document = documents.setdefault(key, {
            "id": key,
            "title": payload.get("title") or "Untitled",
            "source": payload.get("source") or "unknown",
            "filename": payload.get("filename"),
            "created_at": payload.get("document_created_at"),
            "indexing_status": "indexed",
            "legacy": not bool(payload.get("document_id")),
            "chunks": [],
            "content_hashes": set(),
            "versions": {},
        })
        document["chunks"].append({
            "index": payload.get("chunk_index", 0),
            "text": payload.get("text", ""),
            "version_id": payload.get("version_id"),
        })
        if payload.get("version_id"):
            version = document["versions"].setdefault(payload["version_id"], {
                "count": 0,
                "expected": payload.get("expected_chunks"),
            })
            version["count"] += 1
        if payload.get("content_sha256"):
            document["content_hashes"].add(payload["content_sha256"])
        if not document["filename"] and payload.get("filename"):
            document["filename"] = payload["filename"]
        if payload.get("document_created_at") and (
            not document["created_at"] or payload["document_created_at"] < document["created_at"]
        ):
            document["created_at"] = payload["document_created_at"]

    for document in documents.values():
        document["chunks"].sort(key=lambda item: item["index"])
        document["chunk_count"] = len(document["chunks"])
        document["preview"] = document["chunks"][0]["text"][:240] if document["chunks"] else ""
        if not document["legacy"] and len(document["versions"]) > 1:
            document["indexing_status"] = "needs attention"
        elif document["versions"]:
            version = next(iter(document["versions"].values()))
            if version["expected"] and version["count"] < version["expected"]:
                document["indexing_status"] = "incomplete"
        for chunk in document["chunks"]:
            chunk.pop("version_id", None)
        del document["versions"]
        del document["content_hashes"]
    return documents


def list_documents(search: str = "", page: int = 1, page_size: int = 20) -> dict:
    client = get_qdrant_client()
    if not _collection_exists(client):
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    documents = list(_summarize(_scroll_points(client)).values())
    term = search.strip().casefold()
    if term:
        documents = [doc for doc in documents if (
            term in doc["title"].casefold()
            or term in doc["source"].casefold()
            or term in (doc["filename"] or "").casefold()
            or any(term in chunk["text"].casefold() for chunk in doc["chunks"])
        )]
    documents.sort(key=lambda doc: (doc["created_at"] or "", doc["id"]), reverse=True)
    total = len(documents)
    start = (page - 1) * page_size
    items = [{key: value for key, value in doc.items() if key != "chunks"} for doc in documents[start:start + page_size]]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_document(document_id: str) -> dict | None:
    client = get_qdrant_client()
    if not _collection_exists(client):
        return None
    if document_id.startswith("legacy-"):
        documents = _summarize(_scroll_points(client))
        return documents.get(document_id)
    points = _scroll_points(client, Filter(must=[FieldCondition(
        key="document_id", match=MatchValue(value=document_id),
    )]))
    return _summarize(points).get(document_id)


def has_duplicate_content(content_hash: str, except_document_id: str | None = None) -> bool:
    client = get_qdrant_client()
    if not _collection_exists(client):
        return False
    points_filter = Filter(must=[FieldCondition(
        key="content_sha256", match=MatchValue(value=content_hash),
    )])
    matches = _scroll_points(client, points_filter)
    return any(
        (point.payload or {}).get("document_id") != except_document_id
        for point in matches
    )


def delete_document(document_id: str) -> bool:
    client = get_qdrant_client()
    document = get_document(document_id)
    if document is None or document["legacy"]:
        return False
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(must=[FieldCondition(
            key="document_id", match=MatchValue(value=document_id),
        )]),
        wait=True,
    )
    return True
