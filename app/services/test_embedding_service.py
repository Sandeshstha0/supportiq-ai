from app.services.embedding_service import generate_embedding


def test_embedding_generation():
    text = (
        "Customers can contact Lasata Department Stores "
        "for assistance with their purchases."
    )

    vector = generate_embedding(text)

    print("Embedding generated successfully!")
    print("Vector dimensions:", len(vector))
    print("First five values:", vector[:5])

    assert len(vector) == 768


if __name__ == "__main__":
    test_embedding_generation()