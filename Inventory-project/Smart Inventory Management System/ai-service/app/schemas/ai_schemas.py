"""
Pydantic schemas for AI Service request/response contracts.
"""
from typing import Optional
from pydantic import BaseModel, Field


# ── Insights ──────────────────────────────────────────────────────────────────

class InventoryInsightsResponse(BaseModel):
    total_products: int
    total_inventory_value: float
    low_stock_count: int
    out_of_stock_count: int
    healthy_stock_count: int
    low_stock_percentage: float
    currency: str = "USD"


# ── Demand Prediction ─────────────────────────────────────────────────────────

class DemandPredictionRequest(BaseModel):
    product_id: int = Field(..., examples=[1])
    product_name: str = Field(..., examples=["Laptop Pro 15"])
    category: str = Field(..., examples=["Electronics"])
    current_quantity: int = Field(..., ge=0, examples=[45])
    price: float = Field(..., gt=0, examples=[1299.99])


class DemandPredictionResponse(BaseModel):
    product_id: int
    product_name: str
    demand_level: str          # "low" | "medium" | "high"
    confidence: float          # 0.0 – 1.0
    confidence_percentage: float  # 0 – 100
    predicted_daily_sales: float
    reasoning: str


# ── Reorder Suggestion ────────────────────────────────────────────────────────

class ReorderSuggestionRequest(BaseModel):
    product_id: int = Field(..., examples=[1])
    product_name: str = Field(..., examples=["Laptop Pro 15"])
    current_stock: int = Field(..., ge=0, examples=[5])
    minimum_stock: int = Field(..., ge=0, examples=[10])
    average_daily_sales: float = Field(..., ge=0, examples=[3.5])
    lead_time_days: Optional[int] = Field(default=7, ge=1, examples=[7])


class ReorderSuggestionResponse(BaseModel):
    product_id: int
    product_name: str
    current_stock: int
    minimum_stock: int
    reorder_quantity: int
    urgency: str               # "critical" | "high" | "medium" | "low"
    days_until_stockout: Optional[float]
    recommendation: str


# ── Natural Language Query ────────────────────────────────────────────────────

class NLQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["Show me all low stock products"],
    )


class NLQueryResponse(BaseModel):
    original_query: str
    interpreted_intent: str
    result_type: str           # "product_list" | "count" | "value" | "category_stats" | "unknown"
    answer: str                # human-readable answer
    data: Optional[dict] = None  # structured payload for frontend rendering
    suggestions: list[str] = []  # follow-up query suggestions
