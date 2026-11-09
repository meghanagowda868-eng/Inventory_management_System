import pytest

from app.services.festive_discount_policy import recommend_discount, simulate_discount


def test_high_demand_stock_risk_uses_minimum_discount():
    result = recommend_discount(
        minimum_discount=10,
        maximum_discount=25,
        status="REORDER_REQUIRED",
        demand_level="HIGH",
        inventory_surplus=0,
        price=1000,
        unit_cost=700,
    )
    assert result["recommended_discount"] == 10
    assert result["recommended_discount"] <= result["margin_cap"]


def test_low_demand_surplus_uses_maximum_within_margin():
    result = recommend_discount(
        minimum_discount=10,
        maximum_discount=25,
        status="STOCK_READY",
        demand_level="LOW",
        inventory_surplus=0.8,
        price=1000,
        unit_cost=700,
    )
    assert result["recommended_discount"] == 25


def test_simulator_rejects_discount_outside_manager_range():
    with pytest.raises(ValueError, match="manager-configured range"):
        simulate_discount(
            discount_percent=30,
            minimum_discount=10,
            maximum_discount=25,
            predicted_demand=100,
            current_stock=150,
            price=1000,
            unit_cost=700,
            demand_uplift_per_five_percent=0.05,
        )


def test_simulator_reports_actual_margin_and_remaining_stock():
    result = simulate_discount(
        discount_percent=15,
        minimum_discount=10,
        maximum_discount=25,
        predicted_demand=100,
        current_stock=120,
        price=1000,
        unit_cost=700,
        demand_uplift_per_five_percent=0.05,
    )
    assert result["expected_units_sold"] == 115
    assert result["estimated_profit"] == 17250
    assert result["remaining_stock"] == 5