
from app.services.knowledge_search_service import search_knowledge
from app.services.qdrant_service import close_qdrant_client


def test_knowledge_search():
    try:
        query = (
            "What information is stored in the SupportIQ knowledge base?"
        )

        results = search_knowledge(
            query=query,
            limit=5,
        )

        print("\nSearch query:", query)
        print("\nSearch results:")

        for index, result in enumerate(results, start=1):
            print(f"\nResult {index}")
            print("Title:", result["title"])
            print("Source:", result["source"])
            print("Score:", round(result["score"], 4))
            print("Text:", result["text"])

        if results:
            print("\nSUCCESS: Semantic search returned results!")
        else:
            print(
                "\nNo matching documents found. "
                "Check that a document has been stored in Qdrant."
            )

        assert isinstance(results, list)

    finally:
        close_qdrant_client()


if __name__ == "__main__":
    test_knowledge_search()
