
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.ticket import TicketCreate, TicketResponse
from app.services.ticket_service import (
    create_ticket,
    get_ticket_by_id,
    get_tickets_by_guest_session,
)
from app.services.guest_session_service import get_guest_session
from app.services.email_service import send_ticket_confirmation_email

router = APIRouter(
    prefix="/api/v1/tickets",
    tags=["Support Tickets"],
)


def get_valid_guest_session(
    db: Session,
    session_token: str | None,
):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session token is required.",
        )

    guest_session = get_guest_session(db, session_token)

    if guest_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )

    return guest_session



@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_ticket(
    request: TicketCreate,
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    ticket = create_ticket(
        db=db,
        guest_session_id=guest_session.id,
        category=request.category,
        subject=request.subject,
        description=request.description,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        customer_phone=request.customer_phone,
    )

    # Send confirmation only when the customer provides an email.
    if ticket.customer_email:
        send_ticket_confirmation_email(
            recipient=ticket.customer_email,
            customer_name=ticket.customer_name,
            ticket_id=ticket.id,
            subject=ticket.subject,
        )

    return ticket

@router.get("", response_model=list[TicketResponse])
def retrieve_my_tickets(
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    return get_tickets_by_guest_session(
        db=db,
        guest_session_id=guest_session.id,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def retrieve_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    guest_session = get_valid_guest_session(db, session_token)

    ticket = get_ticket_by_id(db, ticket_id)

    if ticket is None or ticket.guest_session_id != guest_session.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    return ticket
