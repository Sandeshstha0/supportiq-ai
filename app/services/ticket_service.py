
from sqlalchemy.orm import Session

from app.models.ticket import SupportTicketDB


def create_ticket(
    db: Session,
    category: str,
    subject: str,
    description: str,
    guest_session_id: int,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> SupportTicketDB:

    ticket = SupportTicketDB(
        guest_session_id=guest_session_id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
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

    return db.get(SupportTicketDB, ticket_id)


def get_tickets_by_guest_session(
    db: Session,
    guest_session_id: int,
) -> list[SupportTicketDB]:

    return (
        db.query(SupportTicketDB)
        .filter(
            SupportTicketDB.guest_session_id == guest_session_id
        )
        .order_by(SupportTicketDB.created_at.desc())
        .all()
    )
