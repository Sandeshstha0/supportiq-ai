
from app.services.knowledge_service import add_document
from app.services.qdrant_service import (
    COLLECTION_NAME,
    close_qdrant_client,
    get_qdrant_client,
)


def test_add_document():
    sample_text = """
    SupportIQ AI Knowledge Base - Test Document

    This is a test document used to verify document storage.
    The SupportIQ AI knowledge base stores information that
    can later be retrieved to answer customer questions.

    Actual store policies must be added from verified documents.
    This test document does not define any return, refund,
    warranty, or delivery policy.
    """

    try:
        result = add_document(
            title="SupportIQ Knowledge Base Test",
            text=sample_text,
            source="test_document",
        )

        print("\nDocument ingestion result:")
        print(result)

        client = get_qdrant_client()

        collection_info = client.get_collection(
            collection_name=COLLECTION_NAME,
        )

        print(
            "\nVectors stored:",
            collection_info.points_count,
        )

        assert result["success"] is True
        assert result["chunks_stored"] > 0

        print("\nSUCCESS: Document stored in Qdrant!")

    finally:
        close_qdrant_client()


if __name__ == "__main__":
    test_add_document()
