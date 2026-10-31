from sqlalchemy.orm import Session

from app.models.ticket import SupportTicketDB


def create_ticket(
    db: Session,
    category: str,
    subject: str,
    description: str,
    customer_name: str | None = None,
    customer_email: str | None = None,
) -> SupportTicketDB:
    """Create and save a customer support ticket."""

    ticket = SupportTicketDB(
        customer_name=customer_name,
        customer_email=customer_email,
        category=category,
        subject=subject,
        description=description,
        status="open",
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


def get_ticket_by_id(
    db: Session,
    ticket_id: int,
) -> SupportTicketDB | None:
    """Retrieve a support ticket by its ID."""

    return db.get(SupportTicketDB, ticket_id)