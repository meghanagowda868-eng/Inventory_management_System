from app.services.festive_policy import assess_festive_stock


def test_reorder_quantity_includes_configured_safety_stock():
    result = assess_festive_stock(
        predicted_demand=500,
        current_stock=280,
        safety_stock_percent=10,
    )

    assert result == {
        "safety_stock": 50,
        "required_stock": 550,
        "stock_gap": 270,
        "recommended_order_quantity": 270,
        "status": "REORDER_REQUIRED",
    }


def test_stock_covering_demand_but_not_buffer_is_monitor():
    result = assess_festive_stock(
        predicted_demand=500,
        current_stock=520,
        safety_stock_percent=10,
    )

    assert result["status"] == "MONITOR"
    assert result["recommended_order_quantity"] == 30


def test_stock_covering_required_stock_is_ready():
    result = assess_festive_stock(
        predicted_demand=500,
        current_stock=550,
        safety_stock_percent=10,
    )

    assert result["status"] == "STOCK_READY"
    assert result["recommended_order_quantity"] == 0