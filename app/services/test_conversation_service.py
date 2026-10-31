
from app.db.database import SessionLocal
from app.services.conversation_service import (
    create_conversation,
    save_message,
    get_conversation_history,
)


def test_conversation_memory():
    db = SessionLocal()

    try:
        # 1. Create a conversation
        conversation = create_conversation(db)
        conversation_id = conversation.id

        print("\nConversation created:", conversation_id)

        # 2. Save a customer message
        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content="I bought damaged rice from your store.",
        )

        # 3. Save an assistant response
        save_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content="I'm sorry about that. I can help you report it.",
        )

        # 4. Save a follow-up message
        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content="Please create a support ticket for it.",
        )

        # 5. Retrieve the conversation history
        history = get_conversation_history(
            db=db,
            conversation_id=conversation_id,
        )

        print("\nConversation history:")

        for message in history:
            print(f"{message['role']}: {message['content']}")

        # 6. Verify the results
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

        print("\nSUCCESS: Conversation memory works!")

    finally:
        db.close()


if __name__ == "__main__":
    test_conversation_memory()
