"""
Smart Reorder Suggestion Service.
Uses the Economic Order Quantity (EOQ) concept with lead time buffer.
"""
import math
from app.schemas.ai_schemas import ReorderSuggestionRequest, ReorderSuggestionResponse


class ReorderService:
    """Compute recommended reorder quantity and urgency."""

    def suggest(self, data: ReorderSuggestionRequest) -> ReorderSuggestionResponse:
        avg_sales = data.average_daily_sales
        lead_time = data.lead_time_days or 7
        current = data.current_stock
        minimum = data.minimum_stock

        # Days until stockout (avoid division by zero)
        if avg_sales > 0:
            days_until_stockout = round(current / avg_sales, 1)
        else:
            days_until_stockout = None

        # Safety stock = cover lead time + 50% buffer
        safety_stock = math.ceil(avg_sales * lead_time * 1.5)

        # Reorder quantity = bring stock up to 2× the safety buffer above minimum
        reorder_quantity = max(
            minimum,
            math.ceil(avg_sales * lead_time * 2) - current + minimum,
        )
        reorder_quantity = max(reorder_quantity, 1)

        # Urgency classification
        urgency = self._classify_urgency(current, minimum, days_until_stockout, lead_time)

        recommendation = self._build_recommendation(
            data.product_name,
            reorder_quantity,
            urgency,
            days_until_stockout,
            lead_time,
            avg_sales,
        )

        return ReorderSuggestionResponse(
            product_id=data.product_id,
            product_name=data.product_name,
            current_stock=current,
            minimum_stock=minimum,
            reorder_quantity=reorder_quantity,
            urgency=urgency,
            days_until_stockout=days_until_stockout,
            recommendation=recommendation,
        )

    @staticmethod
    def _classify_urgency(
        current: int,
        minimum: int,
        days_until_stockout: float | None,
        lead_time: int,
    ) -> str:
        if current == 0:
            return "critical"
        if current < minimum:
            if days_until_stockout and days_until_stockout <= lead_time:
                return "critical"
            return "high"
        if days_until_stockout and days_until_stockout <= lead_time * 1.5:
            return "medium"
        return "low"

    @staticmethod
    def _build_recommendation(
        name: str,
        qty: int,
        urgency: str,
        days: float | None,
        lead_time: int,
        avg_sales: float,
    ) -> str:
        urgency_prefix = {
            "critical": "🚨 URGENT",
            "high":     "⚠️  HIGH PRIORITY",
            "medium":   "📋 RECOMMENDED",
            "low":      "✅ LOW PRIORITY",
        }.get(urgency, "")

        stockout_note = (
            f"Estimated stockout in {days:.0f} days. " if days else "Stock depleted. "
        )
        return (
            f"{urgency_prefix}: Reorder {qty} units of '{name}'. "
            f"{stockout_note}"
            f"Supplier lead time is {lead_time} days. "
            f"Average daily sales: {avg_sales:.1f} units/day."
        )
