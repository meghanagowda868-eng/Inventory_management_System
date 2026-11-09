"""
Product SQLAlchemy model for Inventory Service.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, DECIMAL, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    subcategory_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("subcategories.id"), nullable=True, index=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    model_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    subcategory = relationship("Subcategory", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    inventory_records = relationship("InventoryItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")
    reorder_requests = relationship("ReorderRequest", back_populates="product", cascade="all, delete-orphan")

    @property
    def category_id(self) -> int | None:
        return self.subcategory.category_id if self.subcategory else None

    @property
    def category_name(self) -> str | None:
        return self.subcategory.category.name if self.subcategory and self.subcategory.category else self.category

    @property
    def subcategory_name(self) -> str | None:
        return self.subcategory.name if self.subcategory else None

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None

    @property
    def is_low_stock(self) -> bool:
        """True when quantity is below minimum_stock but > 0."""
        return 0 < self.quantity < self.minimum_stock

    @property
    def is_out_of_stock(self) -> bool:
        """True when quantity is zero."""
        return self.quantity == 0

    @property
    def is_reorder_required(self) -> bool:
        """True when quantity is at or below reorder_point."""
        return self.quantity <= self.reorder_point

    @property
    def stock_status(self) -> str:
        """Human-readable stock status string."""
        if self.is_out_of_stock:
            return "out_of_stock"
        if self.is_low_stock:
            return "low_stock"
        return "available"

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku} qty={self.quantity} reorder_pt={self.reorder_point}>"
