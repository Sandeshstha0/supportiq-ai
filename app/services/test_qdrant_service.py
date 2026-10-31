from app.services.qdrant_service import (
    COLLECTION_NAME,
    get_qdrant_client,
    close_qdrant_client,
)


def test_qdrant_connection():
    client = get_qdrant_client()

    try:
        collections = client.get_collections()

        print("Qdrant connection successful!")
        print("Available collections:", collections.collections)
        print("Knowledge collection name:", COLLECTION_NAME)

    finally:
        close_qdrant_client()


if __name__ == "__main__":
    test_qdrant_connection()