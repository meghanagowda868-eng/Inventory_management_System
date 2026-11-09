"""Tests for system notifications, low-stock scanning, valuation reports, and CSV exports."""
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.dependencies.auth import get_token_data, TokenData
from app.main import app
from app.models.category import Category
from app.models.product import Product
from app.models.notification import Notification
from app.models.subcategory import Subcategory
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


@pytest.fixture
def seed_data(session):
    cat = Category(name="Electronics")
    session.add(cat)
    session.flush()

    subcat = Subcategory(name="Audio", category_id=cat.id)
    session.add(subcat)
    session.flush()

    prod_normal = Product(
        name="Noise Cancelling Headphones",
        category="Electronics",
        subcategory_id=subcat.id,
        sku="NC-HP-900",
        price=200.0,
        unit_cost=120.0,
        quantity=50,
        minimum_stock=10,
        reorder_point=10,
        reorder_quantity=30,
    )
    prod_low = Product(
        name="Studio Microphone",
        category="Electronics",
        subcategory_id=subcat.id,
        sku="MIC-PRO-X",
        price=150.0,
        unit_cost=80.0,
        quantity=3,
        minimum_stock=10,
        reorder_point=10,
        reorder_quantity=20,
    )
    prod_out = Product(
        name="Audio Interface",
        category="Electronics",
        subcategory_id=subcat.id,
        sku="AI-USB-2",
        price=100.0,
        unit_cost=50.0,
        quantity=0,
        minimum_stock=5,
        reorder_point=5,
        reorder_quantity=15,
    )
    session.add_all([prod_normal, prod_low, prod_out])
    session.commit()

    return {
        "prod_normal": prod_normal,
        "prod_low": prod_low,
        "prod_out": prod_out,
    }


def test_notification_lifecycle_and_scan(session, seed_data):
    service = NotificationService(session)

    # 1. Scan stock alerts
    generated = service.scan_and_generate_stock_alerts()
    assert generated == 2  # 1 out of stock (CRITICAL), 1 low stock (WARNING)

    # 2. Check summary
    summary = service.get_summary()
    assert summary.unread_count == 2
    assert summary.critical_count == 2

    # 3. Mark one as read
    notifs = service.list_notifications()
    assert len(notifs) == 2
    service.mark_as_read(notifs[0].id)

    summary_after = service.get_summary()
    assert summary_after.unread_count == 1

    # 4. Mark all read
    service.mark_all_read()
    summary_final = service.get_summary()
    assert summary_final.unread_count == 0


def test_inventory_valuation_and_csv_generation(session, seed_data):
    report_service = ReportService(session)

    # Valuation report
    val = report_service.get_inventory_valuation_report()
    assert val.total_products == 3
    assert val.total_units_in_stock == 53  # 50 + 3 + 0
    # Cost: (50 * 120) + (3 * 80) + (0 * 50) = 6000 + 240 = 6240.0
    assert val.total_cost_value == 6240.0
    # Retail: (50 * 200) + (3 * 150) + (0 * 100) = 10000 + 450 = 10450.0
    assert val.total_retail_value == 10450.0
    assert val.low_stock_product_count == 1
    assert val.out_of_stock_product_count == 1

    # CSV Generation
    csv_text = report_service.generate_inventory_csv()
    assert "Product ID,Product Name,SKU,Category,Stock On Hand" in csv_text
    assert "Noise Cancelling Headphones" in csv_text
    assert "Studio Microphone" in csv_text


# ── Report & Notification API endpoints ──────────────────────────────────────

@pytest.fixture
def app_client(session, seed_data):
    role_holder = {"role": "admin", "user_id": 1, "email": "admin@inventory.local"}

    def override_db():
        yield session

    def override_token():
        return TokenData(
            user_id=role_holder["user_id"],
            email=role_holder["email"],
            role=role_holder["role"],
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_token_data] = override_token

    client = TestClient(app)
    yield client, role_holder, seed_data
    app.dependency_overrides.clear()


def test_reports_and_notifications_api(app_client):
    client, role_holder, _ = app_client

    # Scan alerts
    res_scan = client.post("/notifications/scan-alerts")
    assert res_scan.status_code == 200
    assert res_scan.json()["alerts_generated"] >= 2

    # Get notification summary
    res_summary = client.get("/notifications/summary")
    assert res_summary.status_code == 200
    assert res_summary.json()["unread_count"] >= 2

    # Valuation report
    res_val = client.get("/reports/valuation")
    assert res_val.status_code == 200
    data = res_val.json()
    assert data["total_units_in_stock"] == 53

    # CSV export
    res_csv = client.get("/reports/export/inventory-csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Noise Cancelling Headphones" in res_csv.text
