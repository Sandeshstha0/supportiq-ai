from app.services.gemini_service import generate_response


if __name__ == "__main__":
    answer = generate_response(
        "You are SupportIQ AI, a helpful department store customer "
        "support assistant. Introduce yourself in two sentences."
    )

    print("\nSupportIQ AI:")
    print(answer)