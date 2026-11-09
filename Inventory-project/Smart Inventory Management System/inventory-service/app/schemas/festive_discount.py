"""Schemas for explainable discount recommendations and actual performance."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class FestiveDiscountRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    festival: str = Field(..., min_length=2, max_length=120)
    year: int = Field(..., ge=2000, le=2100)
    minimum_discount: float = Field(..., ge=0, le=100)
    maximum_discount: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def validate_range(self):
        if self.minimum_discount > self.maximum_discount:
            raise ValueError("minimum_discount must not exceed maximum_discount")
        return self


class FestiveDiscountRecommendationResponse(BaseModel):
    product_id: int
    product_name: str
    festival: str
    year: int
    demand_level: str
    inventory_status: str
    current_stock: int
    predicted_demand: int
    minimum_discount: float
    maximum_discount: float
    recommended_discount: float
    margin_cap: float | None
    historical_festival_units: int
    unit_cost_available: bool
    reason: str


class FestiveDiscountSimulationRequest(FestiveDiscountRequest):
    selected_discount: float = Field(..., ge=0, le=100)


class FestiveDiscountSimulationResponse(BaseModel):
    product_id: int
    selected_discount: float
    expected_units_sold: int
    revenue: float
    customer_savings: float
    estimated_profit: float | None
    remaining_stock: int
    profit_available: bool
    assumptions: str


class FestiveDiscountPerformanceCreateRequest(BaseModel):
    festival_event_id: int = Field(..., gt=0)
    campaign_id: int | None = Field(None, gt=0)
    product_id: int = Field(..., gt=0)
    discount_percent: float = Field(..., ge=0, le=100)
    units_sold: int = Field(..., ge=0)
    revenue: Decimal = Field(..., ge=0)
    profit: Decimal | None = Field(None, ge=0)
    campaign_date: date


class FestiveDiscountPerformanceResponse(BaseModel):
    id: int
    festival: str
    campaign_name: str | None
    product_id: int
    product_name: str
    discount_percent: Decimal
    units_sold: int
    revenue: Decimal
    profit: Decimal | None
    campaign_date: date