
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from google.genai.errors import APIError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.conversation import ConversationDB, MessageDB
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation_service import (
    get_conversation,
    save_message,
    get_conversation_history,
)
from app.services.guest_session_service import get_guest_session
from app.services.gemini_service import generate_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
)


def get_valid_guest_session(db: Session, token: str | None):
    """Validate a guest token and return its database session."""

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Guest session token is required.",
        )

    session = get_guest_session(db=db, token=token)

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Guest session is invalid or expired.",
        )

    return session


def get_owned_conversation(
    db: Session,
    conversation_id: int,
    guest_session_id: int,
):
    """Return a conversation only if it belongs to this guest."""

    conversation = get_conversation(db, conversation_id)

    if (
        conversation is None
        or conversation.guest_session_id != guest_session_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    guest_session = get_valid_guest_session(
        db,
        request.session_token,
    )

    if request.conversation_id is None:
        conversation = ConversationDB(
            guest_session_id=guest_session.id,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    else:
        conversation = get_owned_conversation(
            db=db,
            conversation_id=request.conversation_id,
            guest_session_id=guest_session.id,
        )

    conversation_id = conversation.id

    try:
        history = get_conversation_history(
            db=db,
            conversation_id=conversation_id,
            limit=20,
        )

        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        reply = generate_response(
            message=request.message,
            history=history,
            guest_session_id=guest_session.id,
        )

        save_message(
            db=db,
            conversation_id=conversation_id,
            role="assistant",
            content=reply,
        )

        return ChatResponse(
            reply=reply,
            conversation_id=conversation_id,
        )

    except APIError as exc:
        logger.exception("Gemini API request failed")

        raise HTTPException(
            status_code=503,
            detail=(
                "Our AI assistant is temporarily unavailable. "
                "Please try again shortly."
            ),
        ) from exc


# Get conversations belonging to the current guest.
@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    conversations = (
        db.query(ConversationDB)
        .filter(
            ConversationDB.guest_session_id == guest_session.id
        )
        .order_by(ConversationDB.id.desc())
        .all()
    )

    results = []

    for conversation in conversations:
        first_message = (
            db.query(MessageDB)
            .filter(
                MessageDB.conversation_id == conversation.id,
                MessageDB.role == "user",
            )
            .order_by(MessageDB.id.asc())
            .first()
        )

        last_message = (
            db.query(MessageDB)
            .filter(
                MessageDB.conversation_id == conversation.id
            )
            .order_by(MessageDB.id.desc())
            .first()
        )

        title = (
            first_message.content.strip()
            if first_message
            else "New Conversation"
        )

        if len(title) > 45:
            title = title[:45].rsplit(" ", 1)[0] + "..."

        results.append({
            "conversation_id": conversation.id,
            "title": title,
            "last_message": (
                last_message.content
                if last_message
                else ""
            ),
        })

    return {"conversations": results}


# Get messages from a conversation owned by the current guest.
@router.get("/conversations/{conversation_id}")
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        guest_session_id=guest_session.id,
    )

    messages = (
        db.query(MessageDB)
        .filter(
            MessageDB.conversation_id == conversation_id
        )
        .order_by(MessageDB.id.asc())
        .all()
    )

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ],
    }


# Delete a conversation owned by the current guest.
@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    conversation = get_owned_conversation(
        db=db,
        conversation_id=conversation_id,
        guest_session_id=guest_session.id,
    )

    try:
        db.delete(conversation)
        db.commit()

        return {
            "message": "Conversation deleted successfully.",
            "conversation_id": conversation_id,
        }

    except Exception:
        db.rollback()
        logger.exception("Failed to delete conversation")

        raise HTTPException(
            status_code=500,
            detail="Could not delete conversation.",
        )
