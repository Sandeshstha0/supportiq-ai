
import logging

from fastapi import APIRouter, Depends, HTTPException
from google.genai.errors import APIError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation_service import (
    create_conversation,
    get_conversation,
    save_message,
    get_conversation_history,
)
from app.services.gemini_service import generate_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    # Create a new conversation or retrieve an existing one.
    if request.conversation_id is None:
        conversation = create_conversation(db)
    else:
        conversation = get_conversation(
            db,
            request.conversation_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    conversation_id = conversation.id

    try:
        # Retrieve earlier messages BEFORE saving the current message.
        history = get_conversation_history(
            db=db,
            conversation_id=conversation_id,
            limit=20,
        )

        # Save the current customer message.
        save_message(
            db=db,
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        # Generate a reply using the previous conversation history.
        reply = generate_response(
            message=request.message,
            history=history,
        )

        # Save the AI response.
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
