from sqlalchemy.orm import Session

from app.models.ticket import SupportTicketDB
from sqlalchemy import String, cast, or_


VALID_TICKET_STATUSES = {
    "open",
    "in_progress",
    "resolved",
    "closed",
}

TICKET_STATUS_TRANSITIONS = {
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"open", "resolved", "closed"},
    "resolved": {"in_progress", "closed"},
    "closed": {"open", "in_progress"},
}


class TicketStatusTransitionError(ValueError):
    pass


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


# STAFF MANAGEMENT FUNCTIONS


def get_all_tickets(
    db: Session,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:

    query = db.query(SupportTicketDB)

    # Filter by ticket status
    if status:
        query = query.filter(
            SupportTicketDB.status == status
        )

    # Filter by category
    if category:
        query = query.filter(
            SupportTicketDB.category == category
        )

    # Search across customer and ticket details
    if search:
        search_term = f"%{search.strip()}%"
        numeric_id = int(search.strip()) if search.strip().isdigit() else None

        search_filter = or_(
                SupportTicketDB.subject.ilike(search_term),
                SupportTicketDB.customer_name.ilike(search_term),
                SupportTicketDB.customer_email.ilike(search_term),
                SupportTicketDB.customer_phone.ilike(search_term),
                SupportTicketDB.description.ilike(search_term),
                cast(SupportTicketDB.id, String).ilike(search_term),
            )
        if numeric_id is not None:
            search_filter = or_(search_filter, SupportTicketDB.id == numeric_id)
        query = query.filter(search_filter)

    # Count matching tickets before pagination
    total = query.count()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size

    tickets = (
        query
        .order_by(SupportTicketDB.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": tickets,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

def get_staff_ticket_by_id(
    db: Session,
    ticket_id: int,
) -> SupportTicketDB | None:

    return (
        db.query(SupportTicketDB)
        .filter(SupportTicketDB.id == ticket_id)
        .first()
    )

def update_ticket_decision(
    db: Session,
    ticket_id: int,
    decision: str,
    new_status: str,
) -> tuple[SupportTicketDB | None, bool]:

    if new_status not in VALID_TICKET_STATUSES:
        raise TicketStatusTransitionError("Invalid ticket status.")

    ticket = (
        db.query(SupportTicketDB)
        .filter(SupportTicketDB.id == ticket_id)
        .with_for_update()
        .first()
    )

    if ticket is None:
        return None, False

    if (
        new_status != ticket.status
        and new_status not in TICKET_STATUS_TRANSITIONS.get(ticket.status, set())
    ):
        raise TicketStatusTransitionError(
            f"Ticket cannot transition from {ticket.status} to {new_status}."
        )

    changed = ticket.decision != decision or ticket.status != new_status
    if not changed:
        return ticket, False

    ticket.decision = decision
    ticket.status = new_status

    db.commit()
    db.refresh(ticket)

    return ticket, True
