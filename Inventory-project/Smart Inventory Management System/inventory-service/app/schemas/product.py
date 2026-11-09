"""
Pydantic schemas for Inventory Service.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Request Schemas ──────────────────────────────────────────────────────────

class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, examples=["Laptop Pro 15"])
    category: Optional[str] = Field(None, max_length=100, examples=["Electronics"])
    subcategory_id: Optional[int] = Field(None, gt=0)
    supplier_id: Optional[int] = Field(None, gt=0)
    brand: Optional[str] = Field(None, max_length=120)
    model_number: Optional[str] = Field(None, max_length=120)
    sku: str = Field(..., min_length=1, max_length=50, examples=["LAPTOP-PRO-15"])
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0, examples=[1299.99])
    unit_cost: Optional[float] = Field(None, gt=0)
    quantity: int = Field(default=0, ge=0, examples=[50])
    minimum_stock: int = Field(default=10, ge=0, examples=[10])
    reorder_point: int = Field(default=10, ge=0, examples=[10])
    reorder_quantity: int = Field(default=20, gt=0, examples=[20])
    image_url: Optional[str] = Field(None, max_length=500)

    @field_validator("sku")
    @classmethod
    def sku_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("price")
    @classmethod
    def round_price(cls, v: float) -> float:
        return round(v, 2)


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    subcategory_id: Optional[int] = Field(None, gt=0)
    supplier_id: Optional[int] = Field(None, gt=0)
    brand: Optional[str] = Field(None, max_length=120)
    model_number: Optional[str] = Field(None, max_length=120)
    barcode: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    unit_cost: Optional[float] = Field(None, gt=0)
    minimum_stock: Optional[int] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, gt=0)
    image_url: Optional[str] = Field(None, max_length=500)


class StockAdjustRequest(BaseModel):
    """Increase or decrease stock. Use negative delta to decrease."""
    delta: int = Field(..., examples=[10], description="Positive to increase, negative to decrease")
    reason: Optional[str] = Field(None, max_length=255, examples=["Received new shipment"])


# ── Response Schemas ─────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str]
    subcategory_id: Optional[int]
    subcategory_name: Optional[str]
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    brand: Optional[str]
    model_number: Optional[str]
    sku: str
    barcode: Optional[str]
    description: Optional[str]
    price: float
    unit_cost: Optional[float] = None
    quantity: int
    minimum_stock: int
    reorder_point: int = 10
    reorder_quantity: int = 20
    image_url: Optional[str]
    is_active: bool
    stock_status: str          # available | low_stock | out_of_stock
    is_low_stock: bool
    is_out_of_stock: bool
    is_reorder_required: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductOptionResponse(BaseModel):
    id: int
    name: str
    sku: str
    category_id: Optional[int]
    category_name: Optional[str]
    subcategory_id: Optional[int]
    subcategory_name: Optional[str]
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    price: float
    unit_cost: Optional[float]
    quantity: int
    reorder_point: int = 10
    reorder_quantity: int = 20


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StockAdjustResponse(BaseModel):
    product_id: int
    previous_quantity: int
    new_quantity: int
    delta: int
    stock_status: str
    low_stock_alert: bool


class MessageResponse(BaseModel):
    message: str
    success: bool = True
