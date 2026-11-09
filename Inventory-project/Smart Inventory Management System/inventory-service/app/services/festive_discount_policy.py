"""Explainable festive discount and what-if scenario calculations."""
from math import ceil


def recommend_discount(
    *,
    minimum_discount: float,
    maximum_discount: float,
    status: str,
    demand_level: str,
    inventory_surplus: float,
    price: float,
    unit_cost: float | None,
) -> dict[str, float | str | None]:
    if not 0 <= minimum_discount <= maximum_discount <= 100:
        raise ValueError("Discount range must satisfy 0 <= minimum <= maximum <= 100")

    if status == "REORDER_REQUIRED" or demand_level == "HIGH":
        candidate = minimum_discount
        reason = "Stock is tight or predicted demand is high, so the minimum configured discount helps protect availability and margin."
    elif inventory_surplus >= 0.5 and demand_level == "LOW":
        candidate = maximum_discount
        reason = "Stock is high relative to predicted demand, so the maximum configured discount may help reduce excess inventory."
    else:
        candidate = (minimum_discount + maximum_discount) / 2
        reason = "Stock and predicted demand are balanced, so the midpoint of the configured discount range is suggested."

    margin_cap = None
    if unit_cost is not None:
        if price <= 0:
            raise ValueError("Product price must be positive")
        margin_cap = max(0.0, (price - unit_cost) / price * 100)
        if margin_cap < minimum_discount:
            raise ValueError("Configured minimum discount would sell below unit cost")
        candidate = min(candidate, margin_cap)
        reason += " The recommendation is capped at the product's gross-margin break-even discount."

    return {
        "recommended_discount": round(max(minimum_discount, min(candidate, maximum_discount)), 2),
        "minimum_discount": minimum_discount,
        "maximum_discount": maximum_discount,
        "margin_cap": round(margin_cap, 2) if margin_cap is not None else None,
        "reason": reason,
    }


def simulate_discount(
    *,
    discount_percent: float,
    minimum_discount: float,
    maximum_discount: float,
    predicted_demand: int,
    current_stock: int,
    price: float,
    unit_cost: float | None,
    demand_uplift_per_five_percent: float,
) -> dict[str, int | float | None]:
    if not minimum_discount <= discount_percent <= maximum_discount:
        raise ValueError("Selected discount must stay inside the manager-configured range")
    if predicted_demand < 0 or current_stock < 0 or price <= 0:
        raise ValueError("Demand and stock must be non-negative and product price must be positive")
    if unit_cost is not None and price * (1 - discount_percent / 100) < unit_cost:
        raise ValueError("Selected discount would sell below unit cost")

    expected_units = min(
        current_stock,
        ceil(predicted_demand * (1 + (discount_percent / 5) * demand_uplift_per_five_percent)),
    )
    final_price = price * (1 - discount_percent / 100)
    revenue = expected_units * final_price
    profit = expected_units * (final_price - unit_cost) if unit_cost is not None else None
    return {
        "discount_percent": round(discount_percent, 2),
        "expected_units_sold": expected_units,
        "revenue": round(revenue, 2),
        "customer_savings": round(expected_units * price * discount_percent / 100, 2),
        "estimated_profit": round(profit, 2) if profit is not None else None,
        "remaining_stock": current_stock - expected_units,
        "profit_available": unit_cost is not None,
    }