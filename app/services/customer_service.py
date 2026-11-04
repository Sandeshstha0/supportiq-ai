from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import String, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationDB, GuestSessionDB, MessageDB
from app.models.order import OrderDB
from app.models.ticket import SupportTicketDB


IDENTITY_NOTE = (
    "Records are grouped by guest session, not verified person. Separate sessions "
    "are kept separate even when contact details match; one shared session may "
    "also have been used by more than one person. Records without a guest-session "
    "ID are excluded because they cannot be reliably linked to a session."
)


def _order_exists():
    return exists(select(OrderDB.id).where(OrderDB.guest_session_id == GuestSessionDB.id))


def _ticket_exists():
    return exists(select(SupportTicketDB.id).where(SupportTicketDB.guest_session_id == GuestSessionDB.id))


def _profile_query(db: Session):
    return db.query(GuestSessionDB).filter(or_(_order_exists(), _ticket_exists()))


def _sort_time(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _contact_summary(orders: list[OrderDB], tickets: list[SupportTicketDB]) -> dict:
    events = [(row.created_at, row) for row in [*orders, *tickets]]
    events.sort(key=lambda item: _sort_time(item[0]), reverse=True)

    result = {"name": None, "phone": None, "email": None, "location": None}
    for _, row in events:
        for key, attr in (("name", "customer_name"), ("phone", "customer_phone"), ("email", "customer_email")):
            value = getattr(row, attr, None)
            if result[key] is None and value and value.strip():
                result[key] = value.strip()
    for order in sorted(orders, key=lambda row: (_sort_time(row.created_at), row.id), reverse=True):
        if order.delivery_location:
            result["location"] = order.delivery_location
            break
    return result


def _conversation_counts(db: Session, session_ids: list[int]) -> dict[int, int]:
    if not session_ids:
        return {}
    rows = (
        db.query(ConversationDB.guest_session_id, func.count(ConversationDB.id))
        .filter(ConversationDB.guest_session_id.in_(session_ids))
        .group_by(ConversationDB.guest_session_id)
        .all()
    )
    return {session_id: count for session_id, count in rows}


def _customer_row(
    guest_session: GuestSessionDB,
    orders: list[OrderDB],
    tickets: list[SupportTicketDB],
    conversation_count: int,
) -> dict:
    return {
        "customer_id": guest_session.id,
        "identity_type": "guest_session",
        **_contact_summary(orders, tickets),
        "first_seen": guest_session.created_at,
        "order_count": len(orders),
        "ticket_count": len(tickets),
        "conversation_count": conversation_count,
    }


def _summary(db: Session) -> dict:
    return {
        "total_guest_sessions": _profile_query(db).count(),
        "sessions_with_orders": db.query(GuestSessionDB).filter(_order_exists()).count(),
        "sessions_with_tickets": db.query(GuestSessionDB).filter(_ticket_exists()).count(),
    }


def list_customers(
    db: Session,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    summary = _summary(db)
    query = _profile_query(db)

    if search and search.strip():
        term = search.strip()
        pattern = f"%{term}%"
        order_match = exists(select(OrderDB.id).where(
            OrderDB.guest_session_id == GuestSessionDB.id,
            or_(
                OrderDB.customer_name.ilike(pattern),
                OrderDB.customer_phone.ilike(pattern),
                OrderDB.customer_email.ilike(pattern),
            ),
        ))
        ticket_match = exists(select(SupportTicketDB.id).where(
            SupportTicketDB.guest_session_id == GuestSessionDB.id,
            or_(
                SupportTicketDB.customer_name.ilike(pattern),
                SupportTicketDB.customer_phone.ilike(pattern),
                SupportTicketDB.customer_email.ilike(pattern),
            ),
        ))
        query = query.filter(or_(
            cast(GuestSessionDB.id, String).ilike(pattern),
            order_match,
            ticket_match,
        ))

    total = query.count()
    sessions = (
        query.order_by(GuestSessionDB.created_at.desc(), GuestSessionDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    session_ids = [session.id for session in sessions]

    orders_by_session: dict[int, list[OrderDB]] = defaultdict(list)
    tickets_by_session: dict[int, list[SupportTicketDB]] = defaultdict(list)
    if session_ids:
        orders = (
            db.query(OrderDB)
            .filter(OrderDB.guest_session_id.in_(session_ids))
            .order_by(OrderDB.created_at.desc(), OrderDB.id.desc())
            .all()
        )
        tickets = (
            db.query(SupportTicketDB)
            .filter(SupportTicketDB.guest_session_id.in_(session_ids))
            .order_by(SupportTicketDB.created_at.desc(), SupportTicketDB.id.desc())
            .all()
        )
        for order in orders:
            orders_by_session[order.guest_session_id].append(order)
        for ticket in tickets:
            tickets_by_session[ticket.guest_session_id].append(ticket)

    conversation_counts = _conversation_counts(db, session_ids)
    return {
        "items": [
            _customer_row(
                session,
                orders_by_session[session.id],
                tickets_by_session[session.id],
                conversation_counts.get(session.id, 0),
            )
            for session in sessions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "summary": summary,
        "identity_note": IDENTITY_NOTE,
    }


def get_customer_details(db: Session, customer_id: int) -> dict | None:
    session = db.get(GuestSessionDB, customer_id)
    if session is None:
        return None

    orders = (
        db.query(OrderDB)
        .filter(OrderDB.guest_session_id == customer_id)
        .order_by(OrderDB.created_at.desc(), OrderDB.id.desc())
        .all()
    )
    tickets = (
        db.query(SupportTicketDB)
        .filter(SupportTicketDB.guest_session_id == customer_id)
        .order_by(SupportTicketDB.created_at.desc(), SupportTicketDB.id.desc())
        .all()
    )
    if not orders and not tickets:
        return None

    conversations = (
        db.query(ConversationDB)
        .filter(ConversationDB.guest_session_id == customer_id)
        .order_by(ConversationDB.created_at.desc(), ConversationDB.id.desc())
        .all()
    )
    conversation_ids = [conversation.id for conversation in conversations]
    message_rows: dict[int, list[MessageDB]] = defaultdict(list)
    message_counts: dict[int, int] = {}
    if conversation_ids:
        message_counts = {
            conversation_id: count
            for conversation_id, count in (
                db.query(MessageDB.conversation_id, func.count(MessageDB.id))
                .filter(MessageDB.conversation_id.in_(conversation_ids))
                .group_by(MessageDB.conversation_id)
                .all()
            )
        }
        ranked_messages = db.query(
            MessageDB.id.label("id"),
            MessageDB.conversation_id.label("conversation_id"),
            MessageDB.role.label("role"),
            MessageDB.content.label("content"),
            MessageDB.created_at.label("created_at"),
            func.row_number().over(
                partition_by=MessageDB.conversation_id,
                order_by=MessageDB.id.desc(),
            ).label("position"),
        ).filter(MessageDB.conversation_id.in_(conversation_ids)).subquery()
        recent_messages = (
            db.query(ranked_messages)
            .filter(ranked_messages.c.position <= 50)
            .order_by(ranked_messages.c.conversation_id, ranked_messages.c.id)
            .all()
        )
        for row in recent_messages:
            message_rows[row.conversation_id].append(row)

    conversation_history = [
        {
            "id": conversation.id,
            "created_at": conversation.created_at,
            "message_count": message_counts.get(conversation.id, 0),
            "messages": [
                {"role": message.role, "content": message.content, "created_at": message.created_at}
                for message in message_rows[conversation.id]
            ],
        }
        for conversation in conversations
    ]

    activity = [
        {"type": "order_created", "record_id": order.id, "occurred_at": order.created_at, "summary": f"Order #{order.id} placed"}
        for order in orders
    ] + [
        {"type": "ticket_created", "record_id": ticket.id, "occurred_at": ticket.created_at, "summary": f"Support ticket #{ticket.id} created"}
        for ticket in tickets
    ] + [
        {"type": "conversation_started", "record_id": conversation.id, "occurred_at": conversation.created_at, "summary": f"Conversation #{conversation.id} started"}
        for conversation in conversations
    ]
    activity.sort(key=lambda item: _sort_time(item["occurred_at"]), reverse=True)

    profile = _customer_row(session, orders, tickets, len(conversations))
    return {
        **profile,
        "expires_at": session.expires_at,
        "orders": [
            {
                "id": order.id,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_email": order.customer_email,
                "delivery_location": order.delivery_location,
                "ward_number": order.ward_number,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
            }
            for order in orders
        ],
        "tickets": [
            {
                "id": ticket.id,
                "customer_name": ticket.customer_name,
                "customer_email": ticket.customer_email,
                "customer_phone": ticket.customer_phone,
                "category": ticket.category,
                "subject": ticket.subject,
                "status": ticket.status,
                "created_at": ticket.created_at,
            }
            for ticket in tickets
        ],
        "conversations": conversation_history,
        "activity": activity,
    }
