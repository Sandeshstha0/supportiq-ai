
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.order import (
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.order_service import (
    OrderNotFoundError,
    OrderStockError,
    OrderStatusTransitionError,
    VALID_ORDER_STATUSES,
    create_order,
    get_staff_order,
    get_staff_orders,
    update_order_status,
)
from app.services.guest_session_service import get_guest_session
from app.api.dependencies import get_current_user
from app.models.staff import StaffUserDB


router = APIRouter(
    prefix="/api/v1/orders",
    tags=["Orders"],
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_order(
    request: OrderCreate,
    db: Session = Depends(get_db),
    session_token: str | None = Header(
        default=None,
        alias="X-Guest-Session",
    ),
):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session token is required.",
        )

    guest_session = get_guest_session(db, session_token)

    if guest_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest session.",
        )

    # Home delivery is available only in Byas/Damauli wards 2, 3 and 4.
    location = request.delivery_location.lower()

    if (
        "damauli" not in location
        and "byas" not in location
        and "vyas" not in location
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Home delivery is available only in Byas/Damauli.",
        )

    if request.ward_number not in {2, 3, 4}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Home delivery is available only in Byas/Damauli wards 2, 3 and 4.",
        )

    try:
        order = create_order(
            db=db,
            guest_session_id=guest_session.id,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            customer_email=(
                str(request.customer_email)
                if request.customer_email
                else None
            ),
            delivery_location=request.delivery_location,
            ward_number=request.ward_number,
            items=[
                item.model_dump()
                for item in request.items
            ],
        )

        return order

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/staff/all", response_model=OrderListResponse)
def retrieve_staff_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    if status_filter and status_filter not in VALID_ORDER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order status.",
        )

    return get_staff_orders(
        db=db,
        status=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/staff/{order_id}", response_model=OrderResponse)
def retrieve_staff_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    order = get_staff_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order


@router.patch("/staff/{order_id}/status", response_model=OrderResponse)
def change_staff_order_status(
    order_id: int,
    request: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    try:
        return update_order_status(db, order_id, request.status)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    except (OrderStatusTransitionError, OrderStockError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
