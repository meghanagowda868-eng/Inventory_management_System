"""FastAPI router for alerts, notifications, and unread counters."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import TokenData, require_role, get_token_data
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationSummaryResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """List system notifications for the active user."""
    service = NotificationService(db)
    return service.list_notifications(user_id=token.user_id, limit=limit, unread_only=unread_only)


@router.get("/summary", response_model=NotificationSummaryResponse)
def get_notification_summary(
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Get unread counter and most recent notifications."""
    service = NotificationService(db)
    return service.get_summary(user_id=token.user_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_token_data),
):
    """Mark a specific notification as read."""
    service = NotificationService(db)
    try:
        notif = service.mark_as_read(notification_id)
        db.commit()
        return notif
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    token: TokenData = Depends(get_token_data),
):
    """Mark all unread notifications as read."""
    service = NotificationService(db)
    count = service.mark_all_read(user_id=token.user_id)
    db.commit()
    return {"status": "success", "marked_read_count": count}


@router.post("/scan-alerts")
def scan_stock_alerts(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "manager")),
):
    """Scan inventory products and generate alerts for low stock / out of stock items."""
    service = NotificationService(db)
    count = service.scan_and_generate_stock_alerts()
    db.commit()
    return {"status": "success", "alerts_generated": count}
