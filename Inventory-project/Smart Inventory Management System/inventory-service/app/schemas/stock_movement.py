"""Schemas for stock movement analytics."""
from datetime import datetime

from pydantic import BaseModel, Field


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    product_name: str
    warehouse_name: str
    movement_type: str
    quantity: int
    performed_by: str | None = None
    reference: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MovementSummaryItem(BaseModel):
    date: str
    stock_in: int = 0
    stock_out: int = 0
    transfer_in: int = 0
    transfer_out: int = 0
    restock: int = 0
    adjustment: int = 0


class InventoryDashboardSummary(BaseModel):
    total_products: int = 0
    total_stock_units: int = 0
    low_stock_products: int = 0
    out_of_stock_products: int = 0
    overstocked_products: int = 0
    total_warehouses: int = 0
    pending_restock_requests: int = 0
    pending_transfers: int = 0
    inventory_health_score: int = 100


class ProductRiskItem(BaseModel):
    product_id: int
    product_name: str
    sku: str
    quantity: int
    minimum_stock: int
    risk_score: int
    risk_level: str
    recommendation: str


class RiskSnapshotResponse(BaseModel):
    total_at_risk: int = 0
    average_risk_score: int = 0
    items: list[ProductRiskItem] = []
