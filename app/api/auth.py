from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.schemas.auth import StaffLogin, TokenResponse
from app.services.auth_service import (
    verify_password,
    create_access_token,
)
from app.api.dependencies import get_current_user
from app.schemas.auth import StaffCreate, StaffUpdate
from app.api.dependencies import require_admin
from app.services.staff_management_service import (
    LastActiveAdminError,
    StaffConflictError,
    StaffProtectionError,
    create_staff_member,
    get_staff_member,
    list_staff,
    update_staff_member,
    update_staff_status as change_staff_status,
)

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
    try:
        staff = create_staff_member(db, request.model_dump())
    except StaffConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return {
        "message": "Staff account created successfully.",
        "staff": staff,
    }

@router.get("/staff")
def get_all_staff(
    search: str | None = Query(default=None, max_length=100),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    if search is None and page is None and page_size is None:
        staff_members = db.query(StaffUserDB).order_by(
            StaffUserDB.created_at.desc(), StaffUserDB.id.desc(),
        ).all()
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
    return list_staff(
        db,
        search=search,
        page=page or 1,
        page_size=page_size or 20,
    )


@router.get("/staff/{staff_id}")
def retrieve_staff_member(
    staff_id: int,
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    staff = get_staff_member(db, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    return staff


@router.patch("/staff/{staff_id}")
def edit_staff_member(
    staff_id: int,
    request: StaffUpdate,
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    try:
        staff = update_staff_member(
            db,
            staff_id,
            request.model_dump(exclude_unset=True),
            current_admin_id=current_admin.id,
        )
    except StaffConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StaffProtectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff account not found.")
    return {"message": "Staff profile updated successfully.", "staff": staff}

@router.patch("/staff/{staff_id}/status")
def update_staff_status(
    staff_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_admin: StaffUserDB = Depends(require_admin),
):
    try:
        staff = change_staff_status(db, staff_id, is_active, current_admin.id)
    except StaffProtectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LastActiveAdminError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff account not found.")

    return {
        "message": (
            "Staff account activated successfully."
            if is_active
            else "Staff account deactivated successfully."
        ),
        "staff": staff,
    }
