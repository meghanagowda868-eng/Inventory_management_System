"""Campaigns, offers, and normalized offer targeting relationships."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, DECIMAL, ForeignKey, Integer, String, Table, Column, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


offer_products = Table(
    "offer_products",
    Base.metadata,
    Column("offer_id", ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)
offer_categories = Table(
    "offer_categories",
    Base.metadata,
    Column("offer_id", ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)
offer_subcategories = Table(
    "offer_subcategories",
    Base.metadata,
    Column("offer_id", ForeignKey("offers.id", ondelete="CASCADE"), primary_key=True),
    Column("subcategory_id", ForeignKey("subcategories.id", ondelete="CASCADE"), primary_key=True),
)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    banner_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    festival_event_id: Mapped[int | None] = mapped_column(ForeignKey("seasonal_events.id"), nullable=True, index=True)
    minimum_discount: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    maximum_discount: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    selected_discount: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    offers = relationship("Offer", back_populates="campaign")
    festival_event = relationship("SeasonalEvent")

    @property
    def effective_status(self) -> str:
        now = datetime.utcnow()
        if not self.is_enabled:
            return "draft" if self.minimum_discount is not None and self.maximum_discount is not None else "disabled"
        if now < self.starts_at:
            return "scheduled"
        if now > self.ends_at:
            return "expired"
        return "active"


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    minimum_purchase: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0, nullable=False)
    maximum_discount: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    campaign = relationship("Campaign", back_populates="offers")
    products = relationship("Product", secondary=offer_products)
    categories = relationship("Category", secondary=offer_categories)
    subcategories = relationship("Subcategory", secondary=offer_subcategories)

    @property
    def effective_status(self) -> str:
        now = datetime.utcnow()
        if not self.is_enabled:
            return "disabled"
        if now < self.starts_at:
            return "scheduled"
        if now > self.ends_at:
            return "expired"
        return "active"
