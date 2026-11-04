from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.schemas.customer import CustomerDetails, CustomerDirectoryResponse
from app.services.customer_service import get_customer_details, list_customers


router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Staff Customers"],
)


@router.get("/staff/all", response_model=CustomerDirectoryResponse)
def retrieve_customers(
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    return list_customers(db, search=search, page=page, page_size=page_size)


@router.get("/staff/{customer_id}", response_model=CustomerDetails)
def retrieve_customer_details(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    details = get_customer_details(db, customer_id)
    if details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer session not found.",
        )
    return details
