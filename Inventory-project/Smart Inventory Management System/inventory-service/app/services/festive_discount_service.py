"""Explainable festive discount planning built on inventory sales and forecasts."""
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models.discount_history import FestiveDiscountHistory
from app.models.product import Product
from app.models.promotion import Campaign
from app.models.sales_history import SalesHistory, SeasonalEvent
from app.schemas.festive_discount import (
    FestiveDiscountPerformanceCreateRequest,
    FestiveDiscountPerformanceResponse,
    FestiveDiscountRecommendationResponse,
    FestiveDiscountRequest,
    FestiveDiscountSimulationRequest,
    FestiveDiscountSimulationResponse,
)
from app.services.festive_discount_policy import recommend_discount, simulate_discount
from app.services.seasonal_service import SeasonalService


class FestiveDiscountService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _forecast(self, product_id: int, festival: str, year: int):
        forecast = SeasonalService(self.db).forecast_product(
            product_id=product_id,
            festival=festival,
            year=year,
        )
        product = (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.is_active.is_(True))
            .first()
        )
        if not product:
            raise ValueError("Active product not found")
        event = (
            self.db.query(SeasonalEvent)
            .filter(SeasonalEvent.name == forecast.festival, SeasonalEvent.is_active.is_(True))
            .first()
        )
        history_units = self.db.query(SalesHistory).filter(
            SalesHistory.product_id == product_id,
            SalesHistory.event_name == forecast.festival,
        ).with_entities(SalesHistory.quantity).all()
        return forecast, product, event, sum(int(row.quantity) for row in history_units)

    def recommend(self, data: FestiveDiscountRequest) -> FestiveDiscountRecommendationResponse:
        forecast, product, _event, historical_units = self._forecast(data.product_id, data.festival, data.year)
        range_result = recommend_discount(
            minimum_discount=data.minimum_discount,
            maximum_discount=data.maximum_discount,
            status=forecast.status,
            demand_level=forecast.demand_level.upper(),
            inventory_surplus=(forecast.current_stock - forecast.required_stock) / max(1, forecast.required_stock),
            price=float(product.price),
            unit_cost=float(product.unit_cost) if product.unit_cost is not None else None,
        )
        return FestiveDiscountRecommendationResponse(
            product_id=product.id,
            product_name=product.name,
            festival=forecast.festival,
            year=forecast.year,
            demand_level=forecast.demand_level.upper(),
            inventory_status=forecast.status,
            current_stock=forecast.current_stock,
            predicted_demand=forecast.predicted_demand,
            minimum_discount=data.minimum_discount,
            maximum_discount=data.maximum_discount,
            recommended_discount=float(range_result["recommended_discount"]),
            margin_cap=range_result["margin_cap"],
            historical_festival_units=historical_units,
            unit_cost_available=product.unit_cost is not None,
            reason=str(range_result["reason"]),
        )

    def simulate(self, data: FestiveDiscountSimulationRequest) -> FestiveDiscountSimulationResponse:
        forecast, product, _event, _historical_units = self._forecast(data.product_id, data.festival, data.year)
        result = simulate_discount(
            discount_percent=data.selected_discount,
            minimum_discount=data.minimum_discount,
            maximum_discount=data.maximum_discount,
            predicted_demand=forecast.predicted_demand,
            current_stock=forecast.current_stock,
            price=float(product.price),
            unit_cost=float(product.unit_cost) if product.unit_cost is not None else None,
            demand_uplift_per_five_percent=self.settings.festive_discount_demand_uplift_per_five_percent,
        )
        return FestiveDiscountSimulationResponse(
            product_id=product.id,
            selected_discount=float(result["discount_percent"]),
            expected_units_sold=int(result["expected_units_sold"]),
            revenue=float(result["revenue"]),
            customer_savings=float(result["customer_savings"]),
            estimated_profit=float(result["estimated_profit"]) if result["estimated_profit"] is not None else None,
            remaining_stock=int(result["remaining_stock"]),
            profit_available=bool(result["profit_available"]),
            assumptions=f"Scenario estimate only: sales uplift is configured at {self.settings.festive_discount_demand_uplift_per_five_percent * 100:g}% per 5 percentage points of discount, capped by current stock and baseline festive forecast. Replace the uplift assumption with measured elasticity when sales response data is available.",
        )

    def record_performance(
        self,
        data: FestiveDiscountPerformanceCreateRequest,
        *,
        recorded_by: int,
    ) -> FestiveDiscountPerformanceResponse:
        event = self.db.get(SeasonalEvent, data.festival_event_id)
        product = self.db.get(Product, data.product_id)
        campaign = self.db.get(Campaign, data.campaign_id) if data.campaign_id else None
        if not event or not product or not product.is_active:
            raise ValueError("Festival or active product not found")
        if data.campaign_id and not campaign:
            raise ValueError("Campaign not found")
        history = FestiveDiscountHistory(
            festival_event_id=event.id,
            campaign_id=campaign.id if campaign else None,
            product_id=product.id,
            discount_percent=data.discount_percent,
            units_sold=data.units_sold,
            revenue=data.revenue,
            profit=data.profit,
            campaign_date=data.campaign_date,
            recorded_by=recorded_by,
        )
        self.db.add(history)
        self.db.add(SalesHistory(
            product_id=product.id,
            sale_date=data.campaign_date,
            quantity=data.units_sold,
            unit_price=(data.revenue / data.units_sold) if data.units_sold else product.price,
            event_name=event.name,
        ))
        self.db.commit()
        return self._history_response(history, event.name, campaign.name if campaign else None, product.name)

    def list_performance(self, festival_event_id: int | None = None) -> list[FestiveDiscountPerformanceResponse]:
        query = (
            self.db.query(FestiveDiscountHistory)
            .options(
                joinedload(FestiveDiscountHistory.festival_event),
                joinedload(FestiveDiscountHistory.campaign),
                joinedload(FestiveDiscountHistory.product),
            )
            .order_by(FestiveDiscountHistory.campaign_date.desc())
        )
        if festival_event_id:
            query = query.filter(FestiveDiscountHistory.festival_event_id == festival_event_id)
        return [
            self._history_response(row, row.festival_event.name, row.campaign.name if row.campaign else None, row.product.name)
            for row in query.all()
        ]

    @staticmethod
    def _history_response(row, festival: str, campaign_name: str | None, product_name: str):
        return FestiveDiscountPerformanceResponse(
            id=row.id,
            festival=festival,
            campaign_name=campaign_name,
            product_id=row.product_id,
            product_name=product_name,
            discount_percent=row.discount_percent,
            units_sold=row.units_sold,
            revenue=row.revenue,
            profit=row.profit,
            campaign_date=row.campaign_date,
        )