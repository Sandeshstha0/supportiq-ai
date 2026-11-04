from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationDB, MessageDB
from app.models.order import OrderDB
from app.models.ticket import SupportTicketDB


def _has_customer_profile():
    return ConversationDB.guest_session_id.is_not(None) & (exists(select(OrderDB.id).where(
        OrderDB.guest_session_id == ConversationDB.guest_session_id,
    )) | exists(select(SupportTicketDB.id).where(
        SupportTicketDB.guest_session_id == ConversationDB.guest_session_id,
    )))


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def list_staff_conversations(
    db: Session,
    *,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(ConversationDB)
    if search and search.strip():
        term = search.strip()
        if term.isdecimal():
            identifier = int(term)
            query = query.filter(
                (ConversationDB.id == identifier)
                | (ConversationDB.guest_session_id == identifier)
            )
        else:
            query = query.filter(False)
    if date_from:
        query = query.filter(ConversationDB.created_at >= _day_start(date_from))
    if date_to:
        query = query.filter(
            ConversationDB.created_at < _day_start(date_to + timedelta(days=1))
        )

    total = query.count()
    latest_message_times = (
        db.query(
            MessageDB.conversation_id.label("conversation_id"),
            func.max(MessageDB.created_at).label("latest_activity_at"),
        )
        .group_by(MessageDB.conversation_id)
        .subquery()
    )
    conversation_rows = (
        query.outerjoin(latest_message_times, latest_message_times.c.conversation_id == ConversationDB.id)
        .add_columns(latest_message_times.c.latest_activity_at)
        .order_by(func.coalesce(latest_message_times.c.latest_activity_at, ConversationDB.created_at).desc(), ConversationDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ids = [row.id for row, _ in conversation_rows]
    counts: dict[int, int] = {}
    previews: dict[int, str] = {}
    if ids:
        counts = {
            conversation_id: count
            for conversation_id, count in (
                db.query(MessageDB.conversation_id, func.count(MessageDB.id))
                .filter(MessageDB.conversation_id.in_(ids))
                .group_by(MessageDB.conversation_id)
                .all()
            )
        }
        latest = db.query(
            MessageDB.conversation_id,
            MessageDB.content,
            func.row_number().over(
                partition_by=MessageDB.conversation_id,
                order_by=(MessageDB.created_at.desc(), MessageDB.id.desc()),
            ).label("position"),
        ).filter(MessageDB.conversation_id.in_(ids)).subquery()
        previews = {
            conversation_id: content
            for conversation_id, content in db.query(
                latest.c.conversation_id, latest.c.content,
            ).filter(latest.c.position == 1).all()
        }

    profile_session_ids = {
        session_id
        for (session_id,) in db.query(ConversationDB.guest_session_id)
        .filter(ConversationDB.id.in_(ids), _has_customer_profile())
        .all()
    } if ids else set()

    items = []
    for row, latest_activity_at in conversation_rows:
        preview = previews.get(row.id)
        items.append({
            "id": row.id,
            "guest_session_id": row.guest_session_id,
            "created_at": row.created_at,
            "latest_activity_at": latest_activity_at or row.created_at,
            "message_count": counts.get(row.id, 0),
            "preview": preview[:180] if preview else None,
            "has_customer_profile": row.guest_session_id in profile_session_ids,
        })
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def get_staff_conversation(db: Session, conversation_id: int) -> dict | None:
    row = db.get(ConversationDB, conversation_id)
    if row is None:
        return None
    messages = (
        db.query(MessageDB)
        .filter(MessageDB.conversation_id == row.id)
        .order_by(MessageDB.created_at.asc(), MessageDB.id.asc())
        .all()
    )
    profile_exists = db.query(_has_customer_profile()).filter(
        ConversationDB.id == row.id,
    ).scalar()
    latest_activity_at = messages[-1].created_at if messages else row.created_at
    return {
        "id": row.id,
        "guest_session_id": row.guest_session_id,
        "created_at": row.created_at,
        "latest_activity_at": latest_activity_at,
        "message_count": len(messages),
        "preview": messages[-1].content[:180] if messages and messages[-1].content else None,
        "has_customer_profile": bool(profile_exists),
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }
