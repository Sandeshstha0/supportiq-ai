from app.services.gemini_service import search_store_knowledge
from app.services.qdrant_service import close_qdrant_client


def test_rag_integration():
    try:
        result = search_store_knowledge(
            query="What is the SupportIQ knowledge base used for?",
            limit=3,
        )

        print("\nKnowledge search result:")
        print(result)

        assert isinstance(result, dict)
        assert "results" in result
        assert "count" in result

        print("\nSUCCESS: Knowledge search tool works!")

    finally:
        close_qdrant_client()


if __name__ == "__main__":
    test_rag_integration()