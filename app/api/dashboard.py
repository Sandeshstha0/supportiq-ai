from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.staff import StaffUserDB
from app.api.dependencies import get_current_user
from app.services.dashboard_service import (
    get_ticket_dashboard_stats,
    get_recent_tickets,
    get_ticket_category_stats,
    get_ticket_status_distribution,
)

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Staff Dashboard"],
)


@router.get("/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    return get_ticket_dashboard_stats(db)


@router.get("/recent-tickets")
def dashboard_recent_tickets(
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    return get_recent_tickets(db, limit=5)

@router.get("/category-stats")
def dashboard_category_stats(
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    return get_ticket_category_stats(db)

@router.get("/status-distribution")
def dashboard_status_distribution(
    db: Session = Depends(get_db),
    current_user: StaffUserDB = Depends(get_current_user),
):
    return get_ticket_status_distribution(db)