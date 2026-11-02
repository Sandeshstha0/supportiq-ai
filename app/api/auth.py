from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.schemas.auth import StaffLogin, TokenResponse
from app.services.auth_service import (
    verify_password,
    create_access_token,
)
from app.api.dependencies import get_current_user
from app.schemas.auth import StaffCreate
from app.services.auth_service import hash_password
from app.api.dependencies import require_admin

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Staff Authentication"],
)


@router.post("/login", response_model=TokenResponse)
def staff_login(
    request: StaffLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(StaffUserDB)
        .filter(StaffUserDB.username == request.username)
        .first()
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(request.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
    )


@router.get("/me")
def get_my_profile(
    current_user: StaffUserDB = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }

@router.post(
    "/staff",
    status_code=status.HTTP_201_CREATED,
)
def create_staff(
    request: StaffCreate,
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    existing_user = (
        db.query(StaffUserDB)
        .filter(
            (StaffUserDB.username == request.username)
            | (StaffUserDB.email == request.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered.",
        )

    staff = StaffUserDB(
        username=request.username,
        email=str(request.email),
        password_hash=hash_password(request.password),
        role="staff",
        is_active=True,
    )

    db.add(staff)
    db.commit()
    db.refresh(staff)

    return {
        "message": "Staff account created successfully.",
        "staff": {
            "id": staff.id,
            "username": staff.username,
            "email": staff.email,
            "role": staff.role,
            "is_active": staff.is_active,
        },
    }

@router.get("/staff")
def get_all_staff(
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    staff_members = (
        db.query(StaffUserDB)
        .order_by(StaffUserDB.created_at.desc())
        .all()
    )

    return [
        {
            "id": staff.id,
            "username": staff.username,
            "email": staff.email,
            "role": staff.role,
            "is_active": staff.is_active,
            "created_at": staff.created_at,
        }
        for staff in staff_members
    ]

@router.patch("/staff/{staff_id}/status")
def update_staff_status(
    staff_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    staff = db.query(StaffUserDB).filter(
        StaffUserDB.id == staff_id
    ).first()

    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff account not found.",
        )

    # Prevent an admin from deactivating their own account
    if staff.id == current_admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    staff.is_active = is_active

    db.commit()
    db.refresh(staff)

    return {
        "message": (
            "Staff account activated successfully."
            if is_active
            else "Staff account deactivated successfully."
        ),
        "staff": {
            "id": staff.id,
            "username": staff.username,
            "email": staff.email,
            "role": staff.role,
            "is_active": staff.is_active,
        },
    }