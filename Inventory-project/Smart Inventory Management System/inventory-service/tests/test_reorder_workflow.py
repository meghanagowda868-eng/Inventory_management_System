"""End-to-end unit and API tests for the Reorder Management Workflow."""
from datetime import date
from decimal import Decimal
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
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.reorder_request import ReorderRequest
from app.models.stock_movement import StockMovement
from app.models.subcategory import Subcategory
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.services.reorder_service import ReorderService
from app.services.purchase_order_service import PurchaseOrderService
from app.schemas.reorder import ReorderRequestCreate, ReorderRequestReject, ReorderToPOCreateRequest
from app.schemas.purchase_order import ReceiveOrderRequest, ReceiveOrderItemRequest
from app.schemas.supplier import SupplierUpdateRequest


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
    subcat = Subcategory(name="Laptops", category_id=cat.id)
    wh = Warehouse(warehouse_code="WH-MAIN", name="Central Warehouse", status="ACTIVE")
    supp = Supplier(name="Dell Direct", contact_name="Alice Smith", email="alice@dell.com", phone="555-0100", address="100 Dell Way", status="ACTIVE")
    session.add_all([subcat, wh, supp])
    session.flush()

    prod1 = Product(
        name="Dell XPS 15",
        category="Electronics",
        subcategory_id=subcat.id,
        supplier_id=supp.id,
        sku="DELL-XPS-15",
        price=1500.0,
        unit_cost=1000.0,
        quantity=5,
        minimum_stock=10,
        reorder_point=10,
        reorder_quantity=20,
    )
    prod2 = Product(
        name="Logitech Mouse",
        category="Electronics",
        subcategory_id=subcat.id,
        supplier_id=supp.id,
        sku="LOGI-M-1",
        price=50.0,
        unit_cost=30.0,
        quantity=25,
        minimum_stock=10,
        reorder_point=10,
        reorder_quantity=15,
    )
    session.add_all([prod1, prod2])
    session.flush()

    inv1 = InventoryItem(product_id=prod1.id, warehouse_id=wh.id, quantity=5)
    inv2 = InventoryItem(product_id=prod2.id, warehouse_id=wh.id, quantity=25)
    session.add_all([inv1, inv2])
    session.commit()

    return {
        "category": cat,
        "subcategory": subcat,
        "warehouse": wh,
        "supplier": supp,
        "product_low": prod1,
        "product_normal": prod2,
        "inventory_low": inv1,
    }


def test_reorder_detection_logic(session, seed_data):
    service = ReorderService(session)
    recommendations = service.list_reorder_recommendations()

    # prod1 has quantity 5 <= reorder_point 10 -> MUST be detected
    # prod2 has quantity 25 > reorder_point 10 -> MUST NOT be in recommendations
    rec_ids = [r.product_id for r in recommendations]
    assert seed_data["product_low"].id in rec_ids
    assert seed_data["product_normal"].id not in rec_ids

    low_rec = next(r for r in recommendations if r.product_id == seed_data["product_low"].id)
    assert low_rec.current_stock == 5
    assert low_rec.reorder_point == 10
    assert low_rec.reorder_quantity == 20
    assert low_rec.supplier_id == seed_data["supplier"].id
    assert low_rec.has_active_request is False
    assert low_rec.status == "REQUIRED"


def test_create_reorder_request_and_prevent_duplicates(session, seed_data):
    service = ReorderService(session)
    prod = seed_data["product_low"]

    # 1. Create initial reorder request
    req_data = ReorderRequestCreate(
        product_id=prod.id,
        requested_quantity=20,
        reorder_reason="Stock level is below threshold",
    )
    created = service.create_reorder_request(req_data, requested_by=42)
    assert created.status == "PENDING"
    assert created.requested_quantity == 20
    assert created.supplier_id == seed_data["supplier"].id
    assert created.requested_by == 42

    # 2. Try creating duplicate active request for the same product -> MUST fail
    with pytest.raises(ValueError, match="already exists"):
        service.create_reorder_request(req_data, requested_by=42)


def test_reorder_request_approval_and_rejection(session, seed_data):
    service = ReorderService(session)
    prod = seed_data["product_low"]

    # Create request
    created = service.create_reorder_request(
        ReorderRequestCreate(product_id=prod.id, requested_quantity=20),
        requested_by=1,
    )

    # Approve request
    approved = service.approve_reorder_request(created.id, approved_by=99)
    assert approved.status == "APPROVED"
    assert approved.approved_by == 99
    assert approved.approved_at is not None

    # Cannot approve already approved request
    with pytest.raises(ValueError, match="Only PENDING"):
        service.approve_reorder_request(created.id, approved_by=99)

    # Cannot reject already approved request
    with pytest.raises(ValueError, match="Only PENDING"):
        service.reject_reorder_request(created.id, rejection_reason="Too expensive", rejected_by=99)


def test_reorder_request_rejection_requires_reason(session, seed_data):
    service = ReorderService(session)
    prod = seed_data["product_low"]

    created = service.create_reorder_request(
        ReorderRequestCreate(product_id=prod.id, requested_quantity=20),
        requested_by=1,
    )

    # Rejection requires non-empty reason
    with pytest.raises(ValueError, match="Rejection reason is required"):
        service.reject_reorder_request(created.id, rejection_reason="   ", rejected_by=99)

    rejected = service.reject_reorder_request(created.id, rejection_reason="Budget exhausted", rejected_by=99)
    assert rejected.status == "REJECTED"
    assert rejected.rejection_reason == "Budget exhausted"

    # Once rejected, a new request CAN be created for the product
    new_req = service.create_reorder_request(
        ReorderRequestCreate(product_id=prod.id, requested_quantity=15),
        requested_by=2,
    )
    assert new_req.status == "PENDING"
    assert new_req.id != created.id


def test_complete_reorder_to_po_and_partial_to_full_receipt(session, seed_data):
    reorder_service = ReorderService(session)
    po_service = PurchaseOrderService(session)
    prod = seed_data["product_low"]
    wh = seed_data["warehouse"]

    initial_stock = prod.quantity  # 5

    # 1. Create and approve reorder request
    req = reorder_service.create_reorder_request(
        ReorderRequestCreate(product_id=prod.id, requested_quantity=20),
        requested_by=10,
    )
    reorder_service.approve_reorder_request(req.id, approved_by=11)

    # 2. Convert approved reorder request to Purchase Order
    po = reorder_service.create_purchase_order_from_reorder(
        req.id,
        ReorderToPOCreateRequest(warehouse_id=wh.id, expected_delivery=date.today()),
        created_by=11,
    )
    assert po.po_number.startswith("PO-")
    assert po.status == "ORDERED"
    assert po.reorder_request_id == req.id
    assert po.items[0].quantity == 20
    assert po.items[0].received_quantity == 0

    # Verify reorder request status transitioned to ORDERED
    req_db = session.get(ReorderRequest, req.id)
    assert req_db.status == "ORDERED"

    # 3. Partial receipt: Receive 8 of 20
    received_partial = po_service.receive_order(
        po.id,
        received_by=12,
        data=ReceiveOrderRequest(
            items=[ReceiveOrderItemRequest(product_id=prod.id, received_quantity=8)]
        ),
    )
    assert received_partial.status == "PARTIALLY_RECEIVED"
    assert received_partial.items[0].received_quantity == 8
    assert received_partial.items[0].remaining_quantity == 12

    # Verify product and inventory quantities increased by 8
    session.refresh(prod)
    inv = session.get(InventoryItem, seed_data["inventory_low"].id)
    assert prod.quantity == initial_stock + 8  # 5 + 8 = 13
    assert inv.quantity == 13

    # Check stock movement transaction logged
    movements = session.query(StockMovement).filter_by(product_id=prod.id).all()
    assert len(movements) == 1
    assert movements[0].movement_type == "STOCK_IN"
    assert movements[0].quantity == 8
    assert po.po_number in movements[0].reference

    # 4. Attempting to receive more than remaining (e.g. 15 when 12 remain) -> MUST fail
    with pytest.raises(ValueError, match="cannot exceed remaining"):
        po_service.receive_order(
            po.id,
            received_by=12,
            data=ReceiveOrderRequest(
                items=[ReceiveOrderItemRequest(product_id=prod.id, received_quantity=15)]
            ),
        )

    # 5. Receive remaining 12 of 20
    received_full = po_service.receive_order(
        po.id,
        received_by=12,
        data=ReceiveOrderRequest(
            items=[ReceiveOrderItemRequest(product_id=prod.id, received_quantity=12)]
        ),
    )
    assert received_full.status == "RECEIVED"
    assert received_full.items[0].received_quantity == 20
    assert received_full.items[0].remaining_quantity == 0

    session.refresh(prod)
    session.refresh(inv)
    assert prod.quantity == initial_stock + 20  # 5 + 20 = 25
    assert inv.quantity == 25

    # Verify reorder request is now COMPLETED
    session.refresh(req_db)
    assert req_db.status == "COMPLETED"


def test_supplier_crud_operations(session):
    service = PurchaseOrderService(session)

    # Create
    supp = service.create_supplier(
        name="Global Components Inc",
        contact_person="Bob Vance",
        email="bob@vance.com",
        phone="555-1234",
        address="Scranton Industrial Park",
    )
    assert supp.id is not None
    assert supp.name == "Global Components Inc"
    assert supp.contact_person == "Bob Vance"
    assert supp.is_active is True

    # Read
    fetched = service.get_supplier(supp.id)
    assert fetched.name == "Global Components Inc"

    # Update
    updated = service.update_supplier(
        supp.id,
        SupplierUpdateRequest(contact_person="Robert Vance", phone="555-9999"),
    )
    assert updated.contact_person == "Robert Vance"
    assert updated.phone == "555-9999"

    # Delete (Deactivate)
    service.delete_supplier(supp.id)
    deactivated = service.get_supplier(supp.id)
    assert deactivated.is_active is False
    assert deactivated.status == "INACTIVE"


# ── FastAPI TestClient & RBAC Verification ───────────────────────────────────

@pytest.fixture
def app_client(session, seed_data):
    role_holder = {"role": "manager", "user_id": 100, "email": "manager@inventory.local"}

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


def test_rbac_reorder_approval_employee_rejected(app_client):
    client, role_holder, seed_data = app_client

    # 1. As manager, create a reorder request
    role_holder["role"] = "manager"
    create_res = client.post("/inventory/reorders", json={
        "product_id": seed_data["product_low"].id,
        "requested_quantity": 25,
        "reorder_reason": "Low inventory trigger",
    })
    assert create_res.status_code == 201
    reorder_id = create_res.json()["id"]

    # 2. Switch to Employee -> Cannot approve (403 Forbidden)
    role_holder["role"] = "employee"
    approve_res = client.post(f"/inventory/reorders/{reorder_id}/approve")
    assert approve_res.status_code == 403

    # Employee cannot reject (403 Forbidden)
    reject_res = client.post(f"/inventory/reorders/{reorder_id}/reject", json={"rejection_reason": "No budget"})
    assert reject_res.status_code == 403

    # Employee CAN view reorder list & details (200 OK)
    list_res = client.get("/inventory/reorders")
    assert list_res.status_code == 200

    # 3. Switch to Admin -> Can approve (200 OK)
    role_holder["role"] = "admin"
    approve_admin = client.post(f"/inventory/reorders/{reorder_id}/approve")
    assert approve_admin.status_code == 200
    assert approve_admin.json()["status"] == "APPROVED"
