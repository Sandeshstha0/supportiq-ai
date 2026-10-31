from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.ticket import TicketCreate, TicketResponse
from app.services.ticket_service import (
    create_ticket,
    get_ticket_by_id,
)

router = APIRouter(
    prefix="/api/v1/tickets",
    tags=["Support Tickets"],
)


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_ticket(
    request: TicketCreate,
    db: Session = Depends(get_db),
):
    ticket = create_ticket(
        db=db,
        category=request.category,
        subject=request.subject,
        description=request.description,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
    )

    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
def retrieve_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
):
    ticket = get_ticket_by_id(db, ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found",
        )

    return ticket