"""
Mock/synthetic sales data for Phase 1 AI demand prediction.
Structured so a real Sales Service (Phase 3) can replace this.

Data schema matches what the Sales Service will eventually provide:
    product_id, category, avg_daily_sales, price_range, seasonality_factor
"""
import numpy as np
import pandas as pd

# ── Category baseline sales rates ─────────────────────────────────────────────
CATEGORY_BASELINES = {
    "electronics":      {"avg_daily_sales": 4.2,  "volatility": 1.5},
    "clothing":         {"avg_daily_sales": 8.5,  "volatility": 3.0},
    "food & beverage":  {"avg_daily_sales": 25.0, "volatility": 8.0},
    "furniture":        {"avg_daily_sales": 1.2,  "volatility": 0.5},
    "sports":           {"avg_daily_sales": 5.5,  "volatility": 2.0},
    "books":            {"avg_daily_sales": 3.0,  "volatility": 1.0},
    "health":           {"avg_daily_sales": 6.0,  "volatility": 2.5},
    "toys":             {"avg_daily_sales": 7.0,  "volatility": 3.5},
    "automotive":       {"avg_daily_sales": 2.0,  "volatility": 0.8},
    "default":          {"avg_daily_sales": 3.5,  "volatility": 1.5},
}

# ── Price sensitivity tiers ────────────────────────────────────────────────────
def price_demand_factor(price: float) -> float:
    """Higher price → lower demand multiplier."""
    if price < 20:
        return 1.8
    elif price < 100:
        return 1.3
    elif price < 500:
        return 1.0
    elif price < 2000:
        return 0.6
    else:
        return 0.3


def get_baseline_for_category(category: str) -> dict:
    """Return baseline stats for a given category (case-insensitive match)."""
    cat_lower = (category or "").lower()
    for key in CATEGORY_BASELINES:
        if key in cat_lower or cat_lower in key:
            return CATEGORY_BASELINES[key]
    return CATEGORY_BASELINES["default"]


def generate_synthetic_sales_history(
    product_id: int,
    category: str,
    price: float,
    days: int = 90,
) -> pd.DataFrame:
    """
    Generate synthetic daily sales records for a product.
    Used as training/feature data for the demand prediction model.
    """
    np.random.seed(product_id % 1000)  # deterministic per product
    baseline = get_baseline_for_category(category)
    price_factor = price_demand_factor(price)

    base_rate = baseline["avg_daily_sales"] * price_factor
    volatility = baseline["volatility"]

    # Add day-of-week seasonality (weekends slightly higher)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")
    day_of_week_factor = np.where(dates.dayofweek >= 5, 1.3, 1.0)

    daily_sales = np.random.normal(
        loc=base_rate * day_of_week_factor,
        scale=volatility,
        size=days,
    ).clip(min=0).round(1)

    return pd.DataFrame({
        "date": dates,
        "product_id": product_id,
        "quantity_sold": daily_sales,
        "category": category,
        "price": price,
    })


def get_training_dataset() -> pd.DataFrame:
    """
    Build a training dataset from multiple synthetic products.
    Features: avg_daily_sales, price, category_encoded, volatility → label: demand_level
    """
    records = []
    products = [
        (1,  "Electronics",    1299.99),
        (2,  "Electronics",    49.99),
        (3,  "Clothing",       29.99),
        (4,  "Food & Beverage",5.99),
        (5,  "Furniture",      599.99),
        (6,  "Sports",         89.99),
        (7,  "Books",          14.99),
        (8,  "Health",         24.99),
        (9,  "Electronics",    899.00),
        (10, "Clothing",       199.00),
        (11, "Food & Beverage",2.50),
        (12, "Toys",           39.99),
        (13, "Automotive",     249.99),
        (14, "Books",          7.99),
        (15, "Sports",         299.99),
    ]

    for pid, cat, price in products:
        hist = generate_synthetic_sales_history(pid, cat, price, days=90)
        avg_sales = hist["quantity_sold"].mean()
        std_sales = hist["quantity_sold"].std()

        # Label: low / medium / high based on absolute avg daily sales
        if avg_sales < 3:
            label = 0  # low
        elif avg_sales < 8:
            label = 1  # medium
        else:
            label = 2  # high

        records.append({
            "product_id": pid,
            "category": cat,
            "price": price,
            "avg_daily_sales": round(avg_sales, 2),
            "std_daily_sales": round(std_sales, 2),
            "price_demand_factor": price_demand_factor(price),
            "demand_label": label,
        })

    return pd.DataFrame(records)
