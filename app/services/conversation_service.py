
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationDB, MessageDB


def create_conversation(db: Session) -> ConversationDB:
    """Create a new conversation."""
    conversation = ConversationDB()

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation(
    db: Session,
    conversation_id: int,
) -> ConversationDB | None:
    """Retrieve a conversation by its ID."""
    return db.get(ConversationDB, conversation_id)


def save_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
) -> MessageDB:
    """Save a customer or assistant message."""

    if role not in {"user", "assistant"}:
        raise ValueError("Role must be 'user' or 'assistant'.")

    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise ValueError("Conversation not found.")

    message = MessageDB(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_conversation_history(
    db: Session,
    conversation_id: int,
    limit: int = 20,
) -> list[dict[str, str]]:
    """Retrieve the most recent messages in chronological order."""

    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise ValueError("Conversation not found.")

    safe_limit = max(1, min(limit, 50))

    statement = (
        select(MessageDB)
        .where(MessageDB.conversation_id == conversation_id)
        .order_by(MessageDB.id.desc())
        .limit(safe_limit)
    )

    messages = list(db.scalars(statement).all())
    messages.reverse()

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]
