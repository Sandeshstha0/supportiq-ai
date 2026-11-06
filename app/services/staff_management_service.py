from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.staff import StaffUserDB
from app.services.auth_service import hash_password


class StaffConflictError(ValueError):
    pass


class StaffProtectionError(ValueError):
    pass


class LastActiveAdminError(ValueError):
    pass


def _active_admins_for_update(db: Session) -> list[StaffUserDB]:
    return (
        db.query(StaffUserDB)
        .filter(StaffUserDB.role == "admin", StaffUserDB.is_active.is_(True))
        .order_by(StaffUserDB.id.asc())
        .with_for_update()
        .all()
    )


def _staff_data(staff: StaffUserDB, active_admin_count: int = 0) -> dict:
    return {
        "id": staff.id,
        "username": staff.username,
        "email": staff.email,
        "role": staff.role,
        "is_active": staff.is_active,
        "created_at": staff.created_at,
        "is_last_active_admin": (
            staff.role == "admin" and staff.is_active and active_admin_count == 1
        ),
    }


def list_staff(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = db.query(StaffUserDB)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(
            StaffUserDB.username.ilike(pattern),
            StaffUserDB.email.ilike(pattern),
        ))
    total = query.count()
    members = (
        query.order_by(StaffUserDB.created_at.desc(), StaffUserDB.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    active_admin_count = db.query(StaffUserDB).filter(
        StaffUserDB.role == "admin",
        StaffUserDB.is_active.is_(True),
    ).count()
    return {
        "items": [_staff_data(staff, active_admin_count) for staff in members],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "active_admin_count": active_admin_count,
    }


def get_staff_member(db: Session, staff_id: int) -> dict | None:
    staff = db.get(StaffUserDB, staff_id)
    if staff is None:
        return None
    active_admin_count = db.query(StaffUserDB).filter(
        StaffUserDB.role == "admin",
        StaffUserDB.is_active.is_(True),
    ).count()
    return _staff_data(staff, active_admin_count)


def create_staff_member(db: Session, values: dict) -> dict:
    username = values["username"].strip()
    email = str(values["email"]).strip().lower()
    existing = db.query(StaffUserDB.id).filter(or_(
        func.lower(StaffUserDB.username) == username.lower(),
        func.lower(StaffUserDB.email) == email,
    )).first()
    if existing:
        raise StaffConflictError("Username or email is already registered.")

    staff = StaffUserDB(
        username=username,
        email=email,
        password_hash=hash_password(values["password"]),
        role="staff",
        is_active=True,
    )
    db.add(staff)
    try:
        db.commit()
        db.refresh(staff)
    except IntegrityError as exc:
        db.rollback()
        raise StaffConflictError("Username or email is already registered.") from exc
    return get_staff_member(db, staff.id) or _staff_data(staff)


def update_staff_member(
    db: Session,
    staff_id: int,
    values: dict,
    current_admin_id: int,
) -> dict | None:
    staff = db.get(StaffUserDB, staff_id)
    if staff is None:
        return None
    changes = dict(values)
    if "username" in changes:
        changes["username"] = changes["username"].strip()
    if "email" in changes:
        changes["email"] = str(changes["email"]).strip().lower()

    role_change_would_remove_admin = (
        staff.role == "admin"
        and staff.is_active
        and changes.get("role") == "staff"
    )
    if role_change_would_remove_admin:
        if staff_id == current_admin_id:
            raise StaffProtectionError("You cannot demote your own administrator account.")
        active_admins = _active_admins_for_update(db)
        if len(active_admins) <= 1:
            raise LastActiveAdminError("The last active administrator cannot be demoted.")

    if "username" in changes or "email" in changes:
        username = changes.get("username", staff.username)
        email = changes.get("email", staff.email)
        duplicate = db.query(StaffUserDB.id).filter(
            StaffUserDB.id != staff_id,
            or_(
                func.lower(StaffUserDB.username) == username.lower(),
                func.lower(StaffUserDB.email) == email.lower(),
            ),
        ).first()
        if duplicate:
            raise StaffConflictError("Username or email is already registered.")

    for field, value in changes.items():
        setattr(staff, field, value)
    try:
        db.commit()
        db.refresh(staff)
    except IntegrityError as exc:
        db.rollback()
        raise StaffConflictError("Username or email is already registered.") from exc
    return get_staff_member(db, staff_id)


def update_staff_status(
    db: Session,
    staff_id: int,
    is_active: bool,
    current_admin_id: int,
) -> dict | None:
    staff = db.get(StaffUserDB, staff_id)
    if staff is None:
        return None
    if not is_active and staff_id == current_admin_id:
        raise StaffProtectionError("You cannot deactivate your own account.")
    if not is_active and staff.role == "admin" and staff.is_active:
        active_admins = _active_admins_for_update(db)
        if len(active_admins) <= 1:
            raise LastActiveAdminError("The last active administrator cannot be deactivated.")
    staff.is_active = is_active
    db.commit()
    db.refresh(staff)
    return get_staff_member(db, staff_id)
