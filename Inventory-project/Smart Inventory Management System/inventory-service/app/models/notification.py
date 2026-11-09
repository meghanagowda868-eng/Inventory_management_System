"""Notification and stock alert model for real-time notifications."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # Null means broadcast to all managers/admins
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False, index=True)
    # Categories: LOW_STOCK, REORDER, PURCHASE_ORDER, SALE, PROMOTION, SYSTEM
    severity: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    # Severity: INFO, WARNING, CRITICAL, SUCCESS
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    link_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Notification id={self.id} title={self.title} severity={self.severity} read={self.is_read}>"
