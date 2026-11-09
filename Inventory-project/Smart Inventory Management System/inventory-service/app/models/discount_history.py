"""Recorded actual performance for confirmed festive discounts."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, DECIMAL, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class FestiveDiscountHistory(Base):
    __tablename__ = "festive_discount_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    festival_event_id: Mapped[int] = mapped_column(ForeignKey("seasonal_events.id"), nullable=False, index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    discount_percent: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    profit: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2), nullable=True)
    campaign_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recorded_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    festival_event = relationship("SeasonalEvent")
    campaign = relationship("Campaign")
    product = relationship("Product")