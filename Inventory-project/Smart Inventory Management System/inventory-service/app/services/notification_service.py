"""Service for managing system alerts and notifications."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from app.models.notification import Notification
from app.models.product import Product
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationSummaryResponse


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        title: str,
        message: str,
        category: str = "SYSTEM",
        severity: str = "INFO",
        link_url: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            severity=severity,
            link_url=link_url,
            is_read=False,
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_notifications(
        self,
        user_id: Optional[int] = None,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Notification]:
        query = self.db.query(Notification)
        if user_id:
            query = query.filter(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))

        return query.order_by(desc(Notification.created_at)).limit(limit).all()

    def get_summary(self, user_id: Optional[int] = None) -> NotificationSummaryResponse:
        base_query = self.db.query(Notification)
        if user_id:
            base_query = base_query.filter(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))

        unread_count = base_query.filter(Notification.is_read.is_(False)).count()
        critical_count = base_query.filter(
            Notification.is_read.is_(False),
            Notification.severity.in_(["CRITICAL", "WARNING"]),
        ).count()

        recent = (
            base_query.order_by(desc(Notification.created_at))
            .limit(10)
            .all()
        )

        return NotificationSummaryResponse(
            unread_count=unread_count,
            critical_count=critical_count,
            recent_notifications=[NotificationResponse.model_validate(n) for n in recent],
        )

    def mark_as_read(self, notification_id: int) -> Notification:
        notif = self.db.get(Notification, notification_id)
        if not notif:
            raise ValueError(f"Notification with id {notification_id} not found")
        notif.is_read = True
        self.db.flush()
        return notif

    def mark_all_read(self, user_id: Optional[int] = None) -> int:
        query = self.db.query(Notification).filter(Notification.is_read.is_(False))
        if user_id:
            query = query.filter(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
        
        count = query.update({Notification.is_read: True}, synchronize_session=False)
        self.db.flush()
        return count

    def scan_and_generate_stock_alerts(self) -> int:
        """Scan product inventory and create notifications for products below reorder point or 0 stock."""
        products = self.db.query(Product).all()
        alerts_generated = 0

        for prod in products:
            if prod.quantity == 0:
                # Check if we already have an unread critical out-of-stock notification
                exists = (
                    self.db.query(Notification)
                    .filter(
                        Notification.category == "LOW_STOCK",
                        Notification.is_read.is_(False),
                        Notification.title.contains(f"Out of Stock: {prod.name}"),
                    )
                    .first()
                )
                if not exists:
                    self.create_notification(
                        title=f"Out of Stock: {prod.name}",
                        message=f"Product '{prod.name}' (SKU: {prod.sku}) is completely out of stock! Immediate reorder required.",
                        category="LOW_STOCK",
                        severity="CRITICAL",
                        link_url=f"/reorders",
                    )
                    alerts_generated += 1
            elif prod.quantity <= prod.reorder_point:
                exists = (
                    self.db.query(Notification)
                    .filter(
                        Notification.category == "LOW_STOCK",
                        Notification.is_read.is_(False),
                        Notification.title.contains(f"Low Stock: {prod.name}"),
                    )
                    .first()
                )
                if not exists:
                    self.create_notification(
                        title=f"Low Stock: {prod.name}",
                        message=f"Product '{prod.name}' (SKU: {prod.sku}) stock is at {prod.quantity}, below reorder point ({prod.reorder_point}).",
                        category="LOW_STOCK",
                        severity="WARNING",
                        link_url=f"/reorders",
                    )
                    alerts_generated += 1

        return alerts_generated
