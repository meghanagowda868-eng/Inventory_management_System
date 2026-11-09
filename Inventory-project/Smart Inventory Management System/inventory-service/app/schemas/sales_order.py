"""Pydantic schemas for sales order transactions and processing."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SalesOrderItemCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Product ID to sell")
    quantity: int = Field(..., gt=0, description="Quantity to purchase")
    unit_price: Optional[float] = Field(None, ge=0, description="Optional unit price override")
    discount_percent: float = Field(0.0, ge=0, le=100, description="Discount percentage (0-100)")


class SalesOrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=120, description="Customer name")
    customer_email: Optional[str] = Field(None, max_length=120, description="Customer email")
    customer_phone: Optional[str] = Field(None, max_length=50, description="Customer phone")
    channel: str = Field("IN_STORE", description="Sales channel: IN_STORE, ONLINE, B2B")
    payment_method: str = Field("CARD", description="Payment method: CASH, CARD, UPI, BANK_TRANSFER")
    notes: Optional[str] = Field(None, description="Optional order notes")
    items: List[SalesOrderItemCreate] = Field(..., min_length=1, description="Order line items")

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        valid = {"IN_STORE", "ONLINE", "B2B"}
        if v.upper() not in valid:
            raise ValueError(f"Channel must be one of {valid}")
        return v.upper()

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid = {"CASH", "CARD", "UPI", "BANK_TRANSFER"}
        if v.upper() not in valid:
            raise ValueError(f"Payment method must be one of {valid}")
        return v.upper()


class SalesOrderItemResponse(BaseModel):
    id: int
    sales_order_id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: int
    unit_price: float
    unit_cost: float
    discount_percent: float
    discount_amount: float
    line_total: float

    model_config = {"from_attributes": True}


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    channel: str
    payment_method: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    status: str
    notes: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    items: List[SalesOrderItemResponse] = []

    model_config = {"from_attributes": True}


class SalesOrderRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for refund / cancellation")


class SalesSummaryResponse(BaseModel):
    total_orders: int
    total_revenue: float
    total_items_sold: int
    average_order_value: float
    completed_orders: int
    refunded_orders: int
