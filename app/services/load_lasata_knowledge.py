from app.services.lasata_knowledge import LASATA_KNOWLEDGE
from app.services.knowledge_service import add_document
from app.services.qdrant_service import close_qdrant_client


def main():
    try:
        result = add_document(
            title="Lasata Department Store - Customer Support Guide",
            text=LASATA_KNOWLEDGE,
            source="lasata_customer_support",
        )

        print("\nKnowledge Base Upload Result:")
        print(result)

        if not result.get("success"):
            raise RuntimeError("Failed to add Lasata knowledge.")

        print("\nSUCCESS: Lasata knowledge was added to Qdrant.")

    finally:
        close_qdrant_client()


if __name__ == "__main__":
    main()