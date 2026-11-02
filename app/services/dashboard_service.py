from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ticket import SupportTicketDB


def get_ticket_dashboard_stats(db: Session) -> dict:

    total_tickets = db.query(
        func.count(SupportTicketDB.id)
    ).scalar() or 0

    open_tickets = db.query(
        func.count(SupportTicketDB.id)
    ).filter(
        SupportTicketDB.status == "open"
    ).scalar() or 0

    in_progress_tickets = db.query(
        func.count(SupportTicketDB.id)
    ).filter(
        SupportTicketDB.status == "in_progress"
    ).scalar() or 0

    resolved_tickets = db.query(
        func.count(SupportTicketDB.id)
    ).filter(
        SupportTicketDB.status == "resolved"
    ).scalar() or 0

    closed_tickets = db.query(
        func.count(SupportTicketDB.id)
    ).filter(
        SupportTicketDB.status == "closed"
    ).scalar() or 0

    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "resolved_tickets": resolved_tickets,
        "closed_tickets": closed_tickets,
    }

def get_recent_tickets(
    db: Session,
    limit: int = 5,
) -> list[SupportTicketDB]:

    return (
        db.query(SupportTicketDB)
        .order_by(SupportTicketDB.created_at.desc())
        .limit(limit)
        .all()
    )

def get_ticket_category_stats(db: Session) -> list[dict]:

    results = (
        db.query(
            SupportTicketDB.category,
            func.count(SupportTicketDB.id).label("total"),
        )
        .group_by(SupportTicketDB.category)
        .order_by(func.count(SupportTicketDB.id).desc())
        .all()
    )

    return [
        {
            "category": category,
            "total": total,
        }
        for category, total in results
    ]


def get_ticket_status_distribution(db: Session) -> list[dict]:

    results = (
        db.query(
            SupportTicketDB.status,
            func.count(SupportTicketDB.id).label("total"),
        )
        .group_by(SupportTicketDB.status)
        .all()
    )

    total_tickets = sum(total for _, total in results)

    if total_tickets == 0:
        return []

    return [
        {
            "status": ticket_status,
            "total": total,
            "percentage": round((total / total_tickets) * 100, 2),
        }
        for ticket_status, total in results
    ]

