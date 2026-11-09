"""Explainable seasonal demand recommendations."""
from datetime import date, timedelta
import math

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models.category import Category
from app.models.product import Product
from app.models.sales_history import SalesHistory, SeasonalEvent
from app.models.subcategory import Subcategory
from app.schemas.seasonal import (
    DemandRecommendation,
    ProductFestiveForecastResponse,
    SeasonalDemandResponse,
    SeasonalEventCreateRequest,
    SeasonalEventResponse,
)
from app.services.festive_policy import assess_festive_stock


class SeasonalService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _event_status(self, event: SeasonalEvent, today: date) -> str:
        if not event.is_active:
            return "disabled"
        if today < event.start_date:
            return "scheduled"
        if today <= event.end_date:
            return "active"
        return "expired"

    def _event_response(self, event: SeasonalEvent, today: date) -> SeasonalEventResponse:
        return SeasonalEventResponse(
            id=event.id,
            name=event.name,
            start_date=event.start_date,
            end_date=event.end_date,
            description=event.description,
            keywords=[word for word in event.keywords.split(",") if word],
            is_active=event.is_active,
            status=self._event_status(event, today),
        )

    def list_events(self) -> list[SeasonalEventResponse]:
        today = date.today()
        events = self.db.query(SeasonalEvent).order_by(SeasonalEvent.start_date).all()
        return [self._event_response(event, today) for event in events]

    def create_event(self, data: SeasonalEventCreateRequest) -> SeasonalEventResponse:
        if self.db.query(SeasonalEvent).filter(SeasonalEvent.name == data.name.strip()).first():
            raise ValueError(f"Seasonal event '{data.name}' already exists")
        event = SeasonalEvent(
            name=data.name.strip(),
            start_date=data.start_date,
            end_date=data.end_date,
            description=data.description,
            keywords=",".join(sorted({word.strip().lower() for word in data.keywords if word.strip()})),
            is_active=data.is_active,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return self._event_response(event, date.today())

    def _upcoming_event(
        self,
        event_id: int | None = None,
        festival: str | None = None,
        year: int | None = None,
    ) -> SeasonalEvent | None:
        today = date.today()
        query = self.db.query(SeasonalEvent).filter(SeasonalEvent.is_active.is_(True))
        if event_id is not None:
            event = query.filter(SeasonalEvent.id == event_id).first()
            if not event:
                raise ValueError("Seasonal event not found or inactive")
            if year is not None and event.start_date.year != year:
                raise ValueError("Festival does not belong to the selected year")
            return event

        if festival:
            query = query.filter(func.lower(SeasonalEvent.name) == festival.strip().lower())
        if year is not None:
            query = query.filter(
                SeasonalEvent.start_date >= date(year, 1, 1),
                SeasonalEvent.start_date < date(year + 1, 1, 1),
            )
        query = query.order_by(SeasonalEvent.start_date)
        if not festival and year is None:
            query = query.filter(SeasonalEvent.end_date >= today)
        event = query.first()
        if (festival or year is not None) and not event:
            raise ValueError("Festival not found for the selected year")
        return event

    def recommendations(
        self,
        event_id: int | None = None,
        festival: str | None = None,
        year: int | None = None,
        product_id: int | None = None,
        category_id: int | None = None,
    ) -> SeasonalDemandResponse:
        event = self._upcoming_event(event_id=event_id, festival=festival, year=year)
        if not event:
            return SeasonalDemandResponse(
                season="No upcoming season",
                days_remaining=0,
                recommendations=[],
                calculation="Expected demand = recent average daily sales x planning horizon, adjusted by seasonal relevance and trend.",
            )

        today = date.today()
        days_remaining = max(0, (event.start_date - today).days)
        planning_horizon = max(14, min(60, days_remaining or (event.end_date - today).days + 1))
        recent_start = today - timedelta(days=30)
        history_start = today - timedelta(days=90)
        products = (
            self.db.query(Product)
            .options(joinedload(Product.subcategory).joinedload(Subcategory.category))
            .filter(Product.is_active.is_(True))
        )
        if product_id is not None:
            products = products.filter(Product.id == product_id)
        if category_id is not None:
            if not self.db.query(Category.id).filter(Category.id == category_id).first():
                raise ValueError("Category not found")
            products = products.filter(
                Product.subcategory.has(Subcategory.category_id == category_id)
            )
        products = products.all()
        if product_id is not None and not products:
            raise ValueError("Active product not found")
        history_rows = (
            self.db.query(
                SalesHistory.product_id,
                func.coalesce(func.sum(SalesHistory.quantity), 0).label("total_units"),
                func.coalesce(
                    func.sum(case((SalesHistory.sale_date >= recent_start, SalesHistory.quantity), else_=0)),
                    0,
                ).label("recent_units"),
            )
            .filter(
                SalesHistory.sale_date >= history_start,
                SalesHistory.sale_date <= today,
            )
            .group_by(SalesHistory.product_id)
            .all()
        )
        history_by_product = {
            row.product_id: (int(row.total_units or 0), int(row.recent_units or 0))
            for row in history_rows
        }
        recommendations: list[DemandRecommendation] = []
        keywords = [word for word in event.keywords.split(",") if word]
        predicted_demand_total = 0
        baseline_demand_total = 0
        current_stock_total = 0
        stock_gap_total = 0
        products_at_risk = 0
        products_requiring_reorder = 0
        products_to_monitor = 0
        products_ready = 0
        predicted_weekly_total = 0

        for product in products:
            total_units, recent_units = history_by_product.get(product.id, (0, 0))
            average_daily = total_units / 90
            trend_factor = 1.0
            if recent_units > total_units / 3:
                trend_factor = self.settings.festive_sales_trend_factor
            searchable = " ".join(
                [product.name, product.category or "", product.subcategory_name or ""]
            ).lower()
            relevant = any(keyword in searchable for keyword in keywords)
            seasonal_factor = self.settings.festive_relevance_factor if relevant else 1.0
            baseline = math.ceil(average_daily * planning_horizon)
            expected = math.ceil(average_daily * planning_horizon * trend_factor * seasonal_factor)
            change_percent = round((expected / baseline - 1) * 100) if baseline else None
            stock_position = assess_festive_stock(
                predicted_demand=expected,
                current_stock=product.quantity,
                safety_stock_percent=self.settings.festive_safety_stock_percent,
            )
            if total_units == 0:
                stock_position["status"] = "MONITOR"
            if stock_position["status"] == "REORDER_REQUIRED":
                products_requiring_reorder += 1
            elif stock_position["status"] == "MONITOR":
                products_to_monitor += 1
            else:
                products_ready += 1
            predicted_demand_total += expected
            baseline_demand_total += baseline
            current_stock_total += product.quantity
            stock_gap_total += int(stock_position["stock_gap"])
            if stock_position["status"] != "STOCK_READY":
                products_at_risk += 1
            predicted_weekly_total += math.ceil(average_daily * 7 * trend_factor * seasonal_factor)
            if expected <= 0 and product_id is None:
                continue
            reorder = int(stock_position["recommended_order_quantity"])
            if stock_position["status"] == "REORDER_REQUIRED" and expected > product.quantity * 1.5:
                level = "HIGH"
            elif stock_position["status"] != "STOCK_READY":
                level = "MEDIUM"
            else:
                level = "LOW"
            factors = [f"{total_units} units sold in the last 90 days"]
            if trend_factor > 1:
                factors.append("recent sales are trending upward")
            if relevant:
                factors.append(f"{event.name} matches the product category")
            if reorder:
                factors.append("current stock is below required demand and safety stock")
            if total_units == 0:
                factors = ["no recent product sales history is available; validate this estimate before ordering"]
            recommendations.append(DemandRecommendation(
                product_id=product.id,
                product_name=product.name,
                category=product.category_name,
                subcategory=product.subcategory_name,
                current_stock=product.quantity,
                expected_demand=expected,
                baseline_demand=baseline,
                demand_change_percent=change_percent,
                safety_stock=int(stock_position["safety_stock"]),
                required_stock=int(stock_position["required_stock"]),
                stock_gap=int(stock_position["stock_gap"]),
                recommended_order_quantity=reorder,
                status=str(stock_position["status"]),
                demand_level=level,
                suggested_reorder_quantity=reorder,
                reason=f"{product.name} is {level} demand because " + ", ".join(factors) + ".",
            ))

        recommendations.sort(key=lambda item: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item.demand_level], -item.expected_demand))
        try:
            previous_year_start = event.start_date.replace(year=event.start_date.year - 1)
        except ValueError:
            previous_year_start = event.start_date - timedelta(days=365)

        period_offsets = [(-28, -21), (-21, -14), (-14, -7), (-7, 0), (0, 7), (7, 14)]
        period_labels = [
            "4 weeks before",
            "3 weeks before",
            "2 weeks before",
            "1 week before",
            "Festival week",
            "1 week after",
        ]
        period_factors = [0.7, 0.8, 0.9, 1.0, 1.25, 0.75]
        period_ranges = [
            (previous_year_start + timedelta(days=start), previous_year_start + timedelta(days=end))
            for start, end in period_offsets
        ]
        history_start = period_ranges[0][0]
        history_end = period_ranges[-1][1]
        history_columns = [
            func.coalesce(
                func.sum(
                    case(
                        (and_(SalesHistory.sale_date >= start, SalesHistory.sale_date < end), SalesHistory.quantity),
                        else_=0,
                    )
                ),
                0,
            ).label(f"period_{index}")
            for index, (start, end) in enumerate(period_ranges)
        ]
        historical_totals = (
            self.db.query(func.count(SalesHistory.id).label("row_count"), *history_columns)
            .filter(
                SalesHistory.sale_date >= history_start,
                SalesHistory.sale_date < history_end,
                SalesHistory.event_name == event.name,
            )
            .one()
        )
        has_historical_data = historical_totals.row_count > 0
        forecast_periods = [
            {
                "label": label,
                "historical_demand": int(getattr(historical_totals, f"period_{index}") or 0) if has_historical_data else None,
                "predicted_demand": math.ceil(predicted_weekly_total * period_factors[index]),
            }
            for index, label in enumerate(period_labels)
        ]
        demand_change_percent = (
            round((predicted_demand_total / baseline_demand_total - 1) * 100)
            if baseline_demand_total
            else None
        )
        recommendations.sort(key=lambda item: (-item.recommended_order_quantity, -item.expected_demand))
        reorder_products = [
            item for item in recommendations if item.status == "REORDER_REQUIRED"
        ][:100]
        return SeasonalDemandResponse(
            season=event.name,
            event_id=event.id,
            days_remaining=days_remaining,
            planning_horizon_days=planning_horizon,
            predicted_demand=predicted_demand_total,
            baseline_demand=baseline_demand_total,
            demand_change_percent=demand_change_percent,
            current_stock=current_stock_total,
            stock_gap=stock_gap_total,
            recommended_stock=current_stock_total + stock_gap_total,
            products_at_risk=products_at_risk,
            products_requiring_reorder=products_requiring_reorder,
            products_to_monitor=products_to_monitor,
            products_ready=products_ready,
            recommendations=recommendations[:100],
            reorder_products=reorder_products,
            forecast_periods=forecast_periods,
            calculation=f"Expected demand = 90-day average daily sales x planning horizon x trend factor ({self.settings.festive_sales_trend_factor} when sales trend upward) x seasonal relevance factor ({self.settings.festive_relevance_factor} when event keywords match product data). Safety stock is {self.settings.festive_safety_stock_percent}% of predicted demand. Weekly forecast uses a pre-festival profile of 0.70, 0.80, 0.90, 1.00, 1.25, and 0.75 across the six periods. Historical values include only sales tagged with this festival.",
        )

    def forecast_product(
        self,
        *,
        product_id: int,
        festival: str,
        year: int,
    ) -> ProductFestiveForecastResponse:
        event = self._upcoming_event(festival=festival, year=year)
        result = self.recommendations(event_id=event.id, product_id=product_id)
        item = next((recommendation for recommendation in result.recommendations if recommendation.product_id == product_id), None)
        if item is None:
            raise ValueError("Product forecast could not be calculated")
        return ProductFestiveForecastResponse(
            product_id=item.product_id,
            festival=event.name,
            year=event.start_date.year,
            predicted_demand=item.expected_demand,
            baseline_demand=item.baseline_demand,
            current_stock=item.current_stock,
            safety_stock=item.safety_stock,
            required_stock=item.required_stock,
            recommended_order_quantity=item.recommended_order_quantity,
            status=item.status,
            demand_level=item.demand_level,
            reason=item.reason,
        )
