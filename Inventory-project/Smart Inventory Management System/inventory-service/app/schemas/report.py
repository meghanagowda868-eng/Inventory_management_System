"""Pydantic schemas for inventory valuation and sales performance reports."""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class ProductValuationItem(BaseModel):
    product_id: int
    product_name: str
    sku: str
    category: str
    quantity_on_hand: int
    unit_cost: float
    unit_price: float
    total_cost_value: float
    total_retail_value: float
    potential_profit: float
    margin_percent: float
    reorder_point: int
    stock_status: str  # OUT_OF_STOCK, LOW_STOCK, HEALTHY, OVERSTOCKED


class InventoryValuationReport(BaseModel):
    total_products: int
    total_units_in_stock: int
    total_cost_value: float
    total_retail_value: float
    total_potential_profit: float
    overall_margin_percent: float
    low_stock_product_count: int
    out_of_stock_product_count: int
    products: List[ProductValuationItem] = []


class TopSellingProduct(BaseModel):
    product_id: int
    product_name: str
    sku: str
    units_sold: int
    total_revenue: float
    gross_profit: float


class DailySalesMetric(BaseModel):
    date: date
    order_count: int
    units_sold: int
    revenue: float


class SalesPerformanceReport(BaseModel):
    start_date: date
    end_date: date
    total_orders: int
    total_revenue: float
    total_units_sold: int
    total_discount_given: float
    average_order_value: float
    top_products: List[TopSellingProduct] = []
    daily_trends: List[DailySalesMetric] = []
