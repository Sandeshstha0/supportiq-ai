
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.guest_session_service import (
    create_guest_session,
    get_guest_session,
)

router = APIRouter(
    prefix="/api/v1/guest",
    tags=["Guest Sessions"],
)


@router.post("/session")
def create_or_get_session(
    session_token: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Create a new guest session or return an existing valid session.
    """

    # Reuse the existing browser session if it is valid.
    if session_token:
        existing_session = get_guest_session(
            db=db,
            token=session_token,
        )

        if existing_session:
            return {
                "session_token": session_token,
                "session_id": existing_session.id,
                "expires_at": existing_session.expires_at,
            }

    # Otherwise create a new guest session.
    token, session = create_guest_session(db)

    return {
        "session_token": token,
        "session_id": session.id,
        "expires_at": session.expires_at,
    }
