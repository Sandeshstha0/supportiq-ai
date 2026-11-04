from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.schemas.conversation import StaffConversationDetails, StaffConversationPage
from app.services.staff_conversation_service import (
    get_staff_conversation,
    list_staff_conversations,
)


router = APIRouter(prefix="/api/v1/conversations/staff", tags=["Staff Conversations"])


@router.get("/all", response_model=StaffConversationPage)
def retrieve_conversations(
    search: str | None = Query(default=None, max_length=30),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be on or before date_to.")
    return list_staff_conversations(
        db,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=StaffConversationDetails)
def retrieve_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    details = get_staff_conversation(db, conversation_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return details
