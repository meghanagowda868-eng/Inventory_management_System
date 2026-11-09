"""Sales order and order item models for point-of-sale and sales management."""
from datetime import datetime

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    channel: Mapped[str] = mapped_column(String(30), default="IN_STORE", nullable=False)  # IN_STORE, ONLINE, B2B
    payment_method: Mapped[str] = mapped_column(String(30), default="CARD", nullable=False)  # CASH, CARD, UPI, BANK_TRANSFER
    subtotal: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0.0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0.0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0.0, nullable=False)
    total_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED", nullable=False, index=True)  # COMPLETED, REFUNDED, CANCELLED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items = relationship("SalesOrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SalesOrder id={self.id} order_number={self.order_number} total={self.total_amount} status={self.status}>"


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.0, nullable=False)
    discount_percent: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.0, nullable=False)
    line_total: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)

    order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product")

    def __repr__(self) -> str:
        return f"<SalesOrderItem id={self.id} product_id={self.product_id} qty={self.quantity} line_total={self.line_total}>"
