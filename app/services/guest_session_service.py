
import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.conversation import GuestSessionDB


SESSION_DURATION_DAYS = 30


def hash_token(token: str) -> str:
    """Return a SHA-256 hash of the guest session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_guest_session(db: Session) -> tuple[str, GuestSessionDB]:
    """Create a new anonymous guest session."""

    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    session = GuestSessionDB(
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=SESSION_DURATION_DAYS),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return token, session


def get_guest_session(
    db: Session,
    token: str,
) -> GuestSessionDB | None:
    """Find a valid guest session using its token."""

    token_hash = hash_token(token)

    session = (
        db.query(GuestSessionDB)
        .filter(GuestSessionDB.token_hash == token_hash)
        .first()
    )

    if session is None:
        return None

    now = datetime.now(timezone.utc)

    expires_at = session.expires_at

    # Handle databases returning a naive datetime.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        return None

    return session
