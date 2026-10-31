
import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

QDRANT_PATH = os.getenv(
    "QDRANT_PATH",
    "./qdrant_storage",
)

COLLECTION_NAME = "supportiq_knowledge"

# Gemini embedding-001 produces 768-dimensional vectors.
EMBEDDING_DIMENSION = 768

client = QdrantClient(path=QDRANT_PATH)


def get_qdrant_client() -> QdrantClient:
    """Return the local Qdrant client."""
    return client


def create_knowledge_collection() -> None:
    """Create the knowledge collection if it doesn't exist."""
    collections = client.get_collections()

    existing_names = {
        collection.name
        for collection in collections.collections
    }

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )


def close_qdrant_client() -> None:
    """Close the local Qdrant client."""
    client.close()
