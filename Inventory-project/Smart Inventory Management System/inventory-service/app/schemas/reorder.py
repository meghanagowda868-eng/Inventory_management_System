"""Pydantic contracts for Reorder Management System."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ReorderDetectionItem(BaseModel):
    product_id: int
    product_name: str
    sku: str
    category_name: Optional[str] = None
    current_stock: int
    reorder_point: int
    reorder_quantity: int
    unit_cost: Optional[float] = None
    price: float
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    has_active_request: bool = False
    active_reorder_request_id: Optional[int] = None
    active_reorder_status: Optional[str] = None
    status: str  # REQUIRED | NORMAL | PENDING | APPROVED | ORDERED | RECEIVED


class ReorderRequestCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Product ID to reorder")
    supplier_id: Optional[int] = Field(None, gt=0, description="Optional Supplier ID")
    requested_quantity: int = Field(..., gt=0, description="Quantity to reorder, must be > 0")
    reorder_reason: Optional[str] = Field(None, max_length=500, description="Reason for reorder")


class ReorderRequestUpdate(BaseModel):
    requested_quantity: Optional[int] = Field(None, gt=0)
    supplier_id: Optional[int] = Field(None, gt=0)
    reorder_reason: Optional[str] = Field(None, max_length=500)


class ReorderRequestReject(BaseModel):
    rejection_reason: str = Field(..., min_length=2, max_length=500, description="Mandatory reason for rejection")


class ReorderToPOCreateRequest(BaseModel):
    warehouse_id: Optional[int] = Field(default=1, gt=0, description="Destination warehouse ID")
    expected_delivery: Optional[date] = Field(None, description="Expected delivery date")
    unit_cost: Optional[Decimal] = Field(None, gt=0, description="Optional custom unit cost override")
    supplier_id: Optional[int] = Field(None, gt=0, description="Optional supplier ID override")


class ReorderRequestResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    current_stock: int
    reorder_point: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    requested_quantity: int
    reorder_reason: Optional[str] = None
    rejection_reason: Optional[str] = None
    status: str  # PENDING, APPROVED, REJECTED, ORDERED, RECEIVED, COMPLETED
    requested_by: int
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    po_id: Optional[int] = None
    po_number: Optional[str] = None

    model_config = {"from_attributes": True}


class ReorderSummaryResponse(BaseModel):
    products_requiring_reorder: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    orders_in_transit: int = 0
    partially_received_orders: int = 0
    recently_received_stock: int = 0
    total_requests: int = 0
