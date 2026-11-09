"""Tests for Sales Order Processing, stock reductions, order refunds, and inventory ledger integration."""
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
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.stock_movement import StockMovement
from app.models.sales_history import SalesHistory
from app.models.subcategory import Subcategory
from app.models.warehouse import Warehouse
from app.schemas.sales_order import SalesOrderCreate, SalesOrderItemCreate, SalesOrderRefundRequest
from app.services.sales_service import SalesService


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
    cat = Category(name="Laptops & Accessories")
    session.add(cat)
    session.flush()

    subcat = Subcategory(name="Peripherals", category_id=cat.id)
    wh = Warehouse(warehouse_code="WH-EAST", name="East Hub", status="ACTIVE")
    session.add_all([subcat, wh])
    session.flush()

    prod1 = Product(
        name="Mechanical Keyboard",
        category="Electronics",
        subcategory_id=subcat.id,
        sku="KB-MECH-RGB",
        price=100.0,
        unit_cost=60.0,
        quantity=15,
        minimum_stock=5,
        reorder_point=5,
        reorder_quantity=20,
    )
    prod2 = Product(
        name="Gaming Mouse",
        category="Electronics",
        subcategory_id=subcat.id,
        sku="MS-GAME-PRO",
        price=50.0,
        unit_cost=25.0,
        quantity=2,
        minimum_stock=5,
        reorder_point=5,
        reorder_quantity=10,
    )
    session.add_all([prod1, prod2])
    session.flush()

    inv1 = InventoryItem(product_id=prod1.id, warehouse_id=wh.id, quantity=15)
    inv2 = InventoryItem(product_id=prod2.id, warehouse_id=wh.id, quantity=2)
    session.add_all([inv1, inv2])
    session.commit()

    return {
        "product1": prod1,
        "product2": prod2,
        "warehouse": wh,
    }


def test_sales_order_deducts_stock_and_creates_records(session, seed_data):
    service = SalesService(session)
    prod1 = seed_data["product1"]

    order_payload = SalesOrderCreate(
        customer_name="John Doe",
        customer_email="john@example.com",
        customer_phone="555-1122",
        channel="IN_STORE",
        payment_method="CARD",
        notes="First order test",
        items=[
            SalesOrderItemCreate(
                product_id=prod1.id,
                quantity=3,
                discount_percent=10.0,  # 10% off: $100 -> $90 each = $270
            )
        ],
    )

    created_order = service.create_sales_order(order_payload, created_by=10)
    assert created_order.order_number.startswith("SO-")
    assert created_order.customer_name == "John Doe"
    assert created_order.subtotal == 300.0
    assert created_order.discount_amount == 30.0
    assert created_order.total_amount == 270.0
    assert created_order.status == "COMPLETED"

    # Verify product stock deducted: 15 - 3 = 12
    session.refresh(prod1)
    assert prod1.quantity == 12

    # Verify StockMovement ledger
    movements = session.query(StockMovement).filter_by(product_id=prod1.id).all()
    assert len(movements) == 1
    assert movements[0].movement_type == "STOCK_OUT"
    assert movements[0].quantity == 3
    assert created_order.order_number in movements[0].reference

    # Verify SalesHistory logged
    history = session.query(SalesHistory).filter_by(product_id=prod1.id).all()
    assert len(history) == 1
    assert history[0].quantity == 3


def test_sales_order_insufficient_stock_rejected(session, seed_data):
    service = SalesService(session)
    prod2 = seed_data["product2"]  # only 2 in stock

    order_payload = SalesOrderCreate(
        customer_name="Alice Smith",
        channel="ONLINE",
        payment_method="UPI",
        items=[
            SalesOrderItemCreate(
                product_id=prod2.id,
                quantity=5,  # Requesting 5 when only 2 available
            )
        ],
    )

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_sales_order(order_payload, created_by=10)

    # Verify stock remained untouched
    session.refresh(prod2)
    assert prod2.quantity == 2


def test_sales_order_refund_restores_stock(session, seed_data):
    service = SalesService(session)
    prod1 = seed_data["product1"]

    order_payload = SalesOrderCreate(
        customer_name="Bob Wilson",
        channel="IN_STORE",
        payment_method="CASH",
        items=[SalesOrderItemCreate(product_id=prod1.id, quantity=4)],
    )

    order = service.create_sales_order(order_payload, created_by=10)
    session.refresh(prod1)
    assert prod1.quantity == 11  # 15 - 4

    # Now refund order
    refunded = service.refund_sales_order(order.id, user_id=1, reason="Customer returned item")
    assert refunded.status == "REFUNDED"
    assert "Customer returned item" in (refunded.notes or "")

    # Verify inventory is restored back to 15
    session.refresh(prod1)
    assert prod1.quantity == 15

    # Check that a STOCK_IN movement was added
    in_movements = session.query(StockMovement).filter_by(product_id=prod1.id, movement_type="STOCK_IN").all()
    assert len(in_movements) == 1
    assert in_movements[0].quantity == 4


# ── API Endpoint & RBAC verification ─────────────────────────────────────────

@pytest.fixture
def app_client(session, seed_data):
    role_holder = {"role": "employee", "user_id": 50, "email": "clerk@inventory.local"}

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


def test_sales_api_create_and_refund_permissions(app_client):
    client, role_holder, seed_data = app_client
    prod = seed_data["product1"]

    # 1. Employee creates sale (201 Created)
    role_holder["role"] = "employee"
    res = client.post("/sales", json={
        "customer_name": "Walk-in Guest",
        "channel": "IN_STORE",
        "payment_method": "CASH",
        "items": [{"product_id": prod.id, "quantity": 2}],
    })
    assert res.status_code == 201
    order_id = res.json()["id"]

    # 2. Employee tries to refund -> Forbidden (403)
    res_refund_emp = client.post(f"/sales/{order_id}/refund", json={"reason": "Wrong item"})
    assert res_refund_emp.status_code == 403

    # 3. Manager refunds -> Success (200)
    role_holder["role"] = "manager"
    res_refund_mgr = client.post(f"/sales/{order_id}/refund", json={"reason": "Approved by store manager"})
    assert res_refund_mgr.status_code == 200
    assert res_refund_mgr.json()["status"] == "REFUNDED"
