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