"""Configurable festive inventory stock-position calculations."""
from math import ceil


def assess_festive_stock(
    *,
    predicted_demand: int,
    current_stock: int,
    safety_stock_percent: float,
) -> dict[str, int | str]:
    if predicted_demand < 0 or current_stock < 0 or safety_stock_percent < 0:
        raise ValueError("Demand, stock, and safety-stock percentage must be non-negative")

    safety_stock = ceil(predicted_demand * safety_stock_percent / 100)
    required_stock = predicted_demand + safety_stock
    order_quantity = max(0, required_stock - current_stock)

    if current_stock < predicted_demand:
        status = "REORDER_REQUIRED"
    elif current_stock < required_stock:
        status = "MONITOR"
    else:
        status = "STOCK_READY"

    return {
        "safety_stock": safety_stock,
        "required_stock": required_stock,
        "stock_gap": order_quantity,
        "recommended_order_quantity": order_quantity,
        "status": status,
    }