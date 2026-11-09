from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.dependencies.auth import TokenData, get_token_data
from app.main import app
from app.models.category import Category
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.sales_history import SalesHistory, SeasonalEvent
from app.models.subcategory import Subcategory
from app.models.warehouse import Warehouse


@pytest.fixture
def api_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    role = {"value": "manager"}

    def override_db():
        yield db

    def override_token():
        return TokenData(user_id=12, email="manager@test.local", role=role["value"])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_token_data] = override_token
    try:
        category = Category(name="Audio Devices")
        db.add(category)
        db.flush()
        subcategory = Subcategory(name="Bluetooth Speakers", category_id=category.id)
        warehouse = Warehouse(warehouse_code="WH-API", name="API Test Warehouse", status="ACTIVE")
        event = SeasonalEvent(
            name="API Festival",
            start_date=date.today() + timedelta(days=35),
            end_date=date.today() + timedelta(days=40),
            keywords="speaker,audio",
            is_active=True,
        )
        db.add_all([subcategory, warehouse, event])
        db.flush()
        product = Product(
            name="API Bluetooth Speaker",
            category="Electronics",
            subcategory_id=subcategory.id,
            sku="API-SPEAKER-1",
            price=100,
            unit_cost=60,
            quantity=5,
            minimum_stock=2,
        )
        db.add(product)
        db.flush()
        db.add(InventoryItem(product_id=product.id, warehouse_id=warehouse.id, quantity=5))
        db.add(SalesHistory(
            product_id=product.id,
            sale_date=date.today() - timedelta(days=10),
            quantity=90,
            unit_price=100,
            event_name="API Festival",
        ))
        db.commit()
        identifiers = {"category": category.id, "warehouse": warehouse.id, "event": event.id, "product": product.id}

        with TestClient(app) as client:
            yield client, db, role, identifiers
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_manager_can_create_and_receive_order_once(api_context):
    client, db, _role, identifiers = api_context
    supplier_response = client.post("/inventory/suppliers", json={"name": "API Supplier"})
    assert supplier_response.status_code == 201
    supplier_id = supplier_response.json()["id"]

    response = client.post("/inventory/purchase-orders", json={
        "supplier_id": supplier_id,
        "warehouse_id": identifiers["warehouse"],
        "items": [{"product_id": identifiers["product"], "quantity": 4, "unit_cost": 60}],
    })
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert response.json()["status"] == "PENDING_APPROVAL"

    assert client.post(f"/inventory/purchase-orders/{order_id}/approve").status_code == 200
    assert client.post(f"/inventory/purchase-orders/{order_id}/order").status_code == 200
    received = client.post(f"/inventory/purchase-orders/{order_id}/receive")
    assert received.status_code == 200
    assert received.json()["status"] == "RECEIVED"
    assert db.get(Product, identifiers["product"]).quantity == 9

    duplicate = client.post(f"/inventory/purchase-orders/{order_id}/receive")
    assert duplicate.status_code == 400
    assert db.get(Product, identifiers["product"]).quantity == 9


def test_employee_cannot_create_purchase_order(api_context):
    client, _db, role, _identifiers = api_context
    role["value"] = "employee"
    response = client.post("/inventory/purchase-orders", json={
        "supplier_id": 1,
        "warehouse_id": 1,
        "items": [{"product_id": 1, "quantity": 1, "unit_cost": 60}],
    })
    assert response.status_code == 403


def test_product_forecast_and_discount_simulator_use_bounded_values(api_context):
    client, _db, _role, identifiers = api_context
    forecast = client.post("/inventory/seasonal-demand/forecast", json={
        "product_id": identifiers["product"],
        "festival": "API Festival",
        "year": date.today().year,
    })
    assert forecast.status_code == 200
    forecast_data = forecast.json()
    assert forecast_data["required_stock"] == forecast_data["predicted_demand"] + forecast_data["safety_stock"]
    assert forecast_data["recommended_order_quantity"] == max(0, forecast_data["required_stock"] - forecast_data["current_stock"])

    recommendation = client.post("/inventory/festive-discounts/recommend", json={
        "product_id": identifiers["product"],
        "festival": "API Festival",
        "year": date.today().year,
        "minimum_discount": 5,
        "maximum_discount": 20,
    })
    assert recommendation.status_code == 200
    discount = recommendation.json()["recommended_discount"]
    assert 5 <= discount <= 20

    simulation = client.post("/inventory/festive-discounts/simulate", json={
        "product_id": identifiers["product"],
        "festival": "API Festival",
        "year": date.today().year,
        "minimum_discount": 5,
        "maximum_discount": 20,
        "selected_discount": discount,
    })
    assert simulation.status_code == 200
    assert simulation.json()["profit_available"] is True

    outside_range = client.post("/inventory/festive-discounts/simulate", json={
        "product_id": identifiers["product"],
        "festival": "API Festival",
        "year": date.today().year,
        "minimum_discount": 5,
        "maximum_discount": 20,
        "selected_discount": 25,
    })
    assert outside_range.status_code == 400


def test_campaign_requires_explicit_bounded_offer_confirmation(api_context):
    client, db, _role, identifiers = api_context
    event = db.get(SeasonalEvent, identifiers["event"])
    initial_history_count = db.query(SalesHistory).filter_by(product_id=identifiers["product"], event_name=event.name).count()
    campaign = client.post("/inventory/campaigns", json={
        "name": "API Festival Electronics",
        "starts_at": f"{event.start_date.isoformat()}T00:00:00",
        "ends_at": f"{event.end_date.isoformat()}T23:00:00",
        "festival_event_id": event.id,
        "minimum_discount": 5,
        "maximum_discount": 20,
        "selected_discount": 15,
        "is_enabled": False,
    })
    assert campaign.status_code == 201
    campaign_id = campaign.json()["id"]
    assert campaign.json()["status"] == "draft"

    out_of_range = client.post(f"/inventory/campaigns/{campaign_id}/apply-discount", json={
        "selected_discount": 25,
        "product_ids": [identifiers["product"]],
    })
    assert out_of_range.status_code == 400

    applied = client.post(f"/inventory/campaigns/{campaign_id}/apply-discount", json={
        "selected_discount": 15,
        "product_ids": [identifiers["product"]],
    })
    assert applied.status_code == 200
    assert applied.json()["discount_value"] == 15

    performance = client.post("/inventory/festive-discounts/performance", json={
        "festival_event_id": event.id,
        "campaign_id": campaign_id,
        "product_id": identifiers["product"],
        "discount_percent": 15,
        "units_sold": 4,
        "revenue": 340,
        "profit": 100,
        "campaign_date": event.start_date.isoformat(),
    })
    assert performance.status_code == 201
    assert performance.json()["units_sold"] == 4
    assert db.query(SalesHistory).filter_by(product_id=identifiers["product"], event_name=event.name).count() == initial_history_count + 1