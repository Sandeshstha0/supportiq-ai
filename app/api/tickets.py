
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
from app.schemas.ticket import TicketDecisionUpdate
from app.api.dependencies import get_current_user
from app.services.ticket_service import (
    get_all_tickets,
    update_ticket_decision,
    get_staff_ticket_by_id,

)
from app.services.email_service import send_ticket_decision_email
from app.models.staff import StaffUserDB

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

@router.get("/staff/all")
def retrieve_all_tickets(
    status_filter: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    if status_filter and status_filter not in {
        "open",
        "in_progress",
        "resolved",
        "closed",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket status.",
        )

    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be at least 1 and page size must be between 1 and 100.",
        )

    return get_all_tickets(
        db=db,
        status=status_filter,
        category=category,
        search=search,
        page=page,
        page_size=page_size,
    )

@router.get("/staff/{ticket_id}")
def retrieve_staff_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    ticket = get_staff_ticket_by_id(
        db=db,
        ticket_id=ticket_id,
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    return ticket

@router.patch("/{ticket_id}/decision")
def submit_ticket_decision(
    ticket_id: int,
    request: TicketDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    ticket = update_ticket_decision(
        db=db,
        ticket_id=ticket_id,
        decision=request.decision,
        new_status=request.status,
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found.",
        )

    # Notify the customer when an email address is available.
    if ticket.customer_email:
        send_ticket_decision_email(
            recipient=ticket.customer_email,
            customer_name=ticket.customer_name,
            ticket_id=ticket.id,
            subject=ticket.subject,
            decision=ticket.decision,
        )

    return {
        "message": "Ticket decision updated successfully.",
        "ticket": ticket,
    }