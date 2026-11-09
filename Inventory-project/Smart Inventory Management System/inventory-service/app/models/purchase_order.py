"""Purchase orders and line items for manager-confirmed replenishment."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, DECIMAL, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    reorder_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("reorder_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="ORDERED", nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    expected_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    warehouse = relationship("Warehouse")
    reorder_request = relationship("ReorderRequest", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PurchaseOrder id={self.id} po={self.po_number} status={self.status}>"


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (UniqueConstraint("purchase_order_id", "product_id", name="uq_purchase_order_product"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

    @property
    def ordered_quantity(self) -> int:
        return self.quantity

    @property
    def unit_price(self) -> Decimal:
        return self.unit_cost

    @property
    def total_price(self) -> Decimal:
        return self.total_cost

    def __repr__(self) -> str:
        return f"<PurchaseOrderItem id={self.id} po_id={self.purchase_order_id} prod_id={self.product_id} qty={self.quantity} rec={self.received_quantity}>"