
import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

COLLECTION_NAME = "supportiq_knowledge"

# Gemini embedding-001 produces 768-dimensional vectors.
EMBEDDING_DIMENSION = 768

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

QDRANT_PATH = os.getenv(
    "QDRANT_PATH",
    "./qdrant_storage",
)

# Use Qdrant Cloud when credentials are configured.
# Otherwise, use persistent local storage.
if QDRANT_URL and QDRANT_API_KEY:
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )
    print("Connected to Qdrant Cloud")

else:
    client = QdrantClient(
        path=os.path.abspath(QDRANT_PATH)
    )
    print(
        "Using local Qdrant storage:",
        os.path.abspath(QDRANT_PATH),
    )


def get_qdrant_client() -> QdrantClient:
    """Return the configured Qdrant client."""
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

        print(f"Created Qdrant collection: {COLLECTION_NAME}")

    else:
        print(f"Qdrant collection already exists: {COLLECTION_NAME}")


def close_qdrant_client() -> None:
    """Close the Qdrant client."""
    client.close()
