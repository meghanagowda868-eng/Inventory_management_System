"""Validated supplier and purchase-order API contracts."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Re-export Supplier schemas for backward compatibility
from app.schemas.supplier import (  # noqa: F401
    SupplierCreateRequest,
    SupplierResponse,
    SupplierUpdateRequest,
)


class PurchaseOrderItemCreateRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    unit_cost: Optional[Decimal] = Field(None, gt=0)


class PurchaseOrderCreateRequest(BaseModel):
    supplier_id: int = Field(..., gt=0)
    warehouse_id: int = Field(default=1, gt=0)
    reorder_request_id: Optional[int] = Field(None, gt=0)
    expected_delivery: Optional[date] = None
    items: list[PurchaseOrderItemCreateRequest] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_products(self):
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product can appear only once in a purchase order")
        return self


class ReceiveOrderItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    received_quantity: int = Field(..., gt=0)


class ReceiveOrderRequest(BaseModel):
    items: Optional[list[ReceiveOrderItemRequest]] = None
    received_quantity: Optional[int] = Field(None, gt=0, description="Single item convenience receipt quantity")


class PurchaseOrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    quantity: int
    ordered_quantity: int
    unit_cost: Decimal
    unit_price: Decimal
    total_cost: Decimal
    total_price: Decimal
    received_quantity: int
    remaining_quantity: int

    model_config = {"from_attributes": True}


class PurchaseOrderResponse(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    supplier_name: str
    warehouse_id: int
    warehouse_name: str
    reorder_request_id: Optional[int] = None
    status: str  # DRAFT, ORDERED, PARTIALLY_RECEIVED, RECEIVED, CANCELLED
    order_date: date
    expected_delivery: Optional[date] = None
    total_amount: Decimal
    created_by: int
    approved_by: Optional[int] = None
    received_by: Optional[int] = None
    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: list[PurchaseOrderItemResponse]

    model_config = {"from_attributes": True}