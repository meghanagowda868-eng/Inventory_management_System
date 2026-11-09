"""Reorder request model representing business replenishment workflow."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class ReorderRequest(Base):
    __tablename__ = "reorder_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product = relationship("Product", back_populates="reorder_requests")
    supplier = relationship("Supplier", back_populates="reorder_requests")
    purchase_orders = relationship("PurchaseOrder", back_populates="reorder_request")

    def __repr__(self) -> str:
        return f"<ReorderRequest id={self.id} product_id={self.product_id} qty={self.requested_quantity} status={self.status}>"
