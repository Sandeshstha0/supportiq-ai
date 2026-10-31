
from app.services.embedding_service import generate_embedding
from app.services.qdrant_service import (
    COLLECTION_NAME,
    get_qdrant_client,
)


def search_knowledge(
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Search the knowledge base using semantic similarity.

    Returns the most relevant document passages.
    """

    query = query.strip()

    if not query:
        return []

    safe_limit = max(1, min(limit, 10))

    client = get_qdrant_client()

    # Check whether the knowledge collection exists.
    collections = client.get_collections()

    collection_names = {
        collection.name
        for collection in collections.collections
    }

    if COLLECTION_NAME not in collection_names:
        return []

    # Convert the customer's question into an embedding.
    query_vector = generate_embedding(query)

    # Search for semantically similar document passages.
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=safe_limit,
        with_payload=True,
    ).points

    matches = []

    for point in results:
        payload = point.payload or {}

        matches.append(
            {
                "title": payload.get("title", "Untitled"),
                "source": payload.get("source", "unknown"),
                "text": payload.get("text", ""),
                "score": float(point.score),
            }
        )

    return matches
