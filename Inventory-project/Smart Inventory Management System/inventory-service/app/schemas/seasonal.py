"""Schemas for explainable seasonal demand recommendations."""
from datetime import date

from pydantic import BaseModel, Field, model_validator


class SeasonalEventCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    start_date: date
    end_date: date
    description: str | None = Field(None, max_length=500)
    keywords: list[str] = Field(default_factory=list)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SeasonalEventResponse(BaseModel):
    id: int
    name: str
    start_date: date
    end_date: date
    description: str | None
    keywords: list[str]
    is_active: bool
    status: str


class DemandRecommendation(BaseModel):
    product_id: int
    product_name: str
    category: str | None
    subcategory: str | None
    current_stock: int
    expected_demand: int
    baseline_demand: int
    demand_change_percent: int | None
    safety_stock: int = 0
    required_stock: int = 0
    stock_gap: int = 0
    recommended_order_quantity: int = 0
    status: str = "STOCK_READY"
    demand_level: str
    suggested_reorder_quantity: int
    reason: str


class SeasonalDemandResponse(BaseModel):
    season: str
    event_id: int | None = None
    days_remaining: int
    planning_horizon_days: int = 0
    predicted_demand: int = 0
    baseline_demand: int = 0
    demand_change_percent: int | None = None
    current_stock: int = 0
    stock_gap: int = 0
    recommended_stock: int = 0
    products_at_risk: int = 0
    products_requiring_reorder: int = 0
    products_to_monitor: int = 0
    products_ready: int = 0
    recommendations: list[DemandRecommendation]
    reorder_products: list[DemandRecommendation] = Field(default_factory=list)
    forecast_periods: list["SeasonalForecastPeriod"] = Field(default_factory=list)
    calculation: str


class SeasonalForecastPeriod(BaseModel):
    label: str
    historical_demand: int | None
    predicted_demand: int


class SeasonalForecastRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    festival: str = Field(..., min_length=2, max_length=120)
    year: int = Field(..., ge=2000, le=2100)


class ProductFestiveForecastResponse(BaseModel):
    product_id: int
    festival: str
    year: int
    predicted_demand: int
    baseline_demand: int
    current_stock: int
    safety_stock: int
    required_stock: int
    recommended_order_quantity: int
    status: str
    demand_level: str
    reason: str
