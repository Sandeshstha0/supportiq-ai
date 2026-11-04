
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import create_order
from app.services.guest_session_service import get_guest_session


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
