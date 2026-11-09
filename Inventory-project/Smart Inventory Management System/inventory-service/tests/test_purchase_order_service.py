import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.category import Category
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.subcategory import Subcategory
from app.models.warehouse import Warehouse
from app.services.purchase_order_service import PurchaseOrderService


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


def test_receiving_approved_order_updates_stock_once(session):
    category = Category(name="Computers")
    session.add(category)
    session.flush()
    subcategory = Subcategory(name="Laptops", category_id=category.id)
    warehouse = Warehouse(warehouse_code="WH-TEST", name="Test Warehouse")
    session.add_all([subcategory, warehouse])
    session.flush()
    product = Product(
        name="Test Laptop",
        category="Electronics",
        subcategory_id=subcategory.id,
        sku="TEST-LAPTOP-1",
        price=1000,
        unit_cost=700,
        quantity=10,
        minimum_stock=2,
    )
    session.add(product)
    session.flush()
    inventory = InventoryItem(product_id=product.id, warehouse_id=warehouse.id, quantity=10)
    session.add(inventory)
    session.commit()

    service = PurchaseOrderService(session)
    supplier = service.create_supplier(name="Test Supplier")
    order = service.create_order(
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        expected_delivery=None,
        created_by=7,
        items=[{"product_id": product.id, "quantity": 5, "unit_cost": 700}],
    )
    service.approve_order(order.id, approved_by=7)
    service.mark_ordered(order.id)

    received = service.receive_order(order.id, received_by=7)
    assert received.status == "RECEIVED"
    assert session.get(Product, product.id).quantity == 15
    assert session.get(InventoryItem, inventory.id).quantity == 15
    assert session.query(StockMovement).filter_by(product_id=product.id).count() == 1

    with pytest.raises(ValueError, match="already received"):
        service.receive_order(order.id, received_by=7)

    assert session.get(Product, product.id).quantity == 15
    assert session.get(InventoryItem, inventory.id).quantity == 15
    assert session.query(StockMovement).filter_by(product_id=product.id).count() == 1