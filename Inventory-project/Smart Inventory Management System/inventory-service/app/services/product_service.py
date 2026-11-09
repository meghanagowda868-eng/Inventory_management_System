"""
Product Service — business logic for the Inventory Service.
"""
import math
from typing import Optional

from sqlalchemy.orm import Session

from app.events.stock_events import build_stock_event, emit_stock_event
from app.repositories.product_repository import ProductRepository
from app.repositories.stock_movement_repository import StockMovementRepository
from app.repositories.subcategory_repository import SubcategoryRepository
from app.models.supplier import Supplier
from app.schemas.product import (
    MessageResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductOptionResponse,
    ProductResponse,
    ProductUpdateRequest,
    StockAdjustRequest,
    StockAdjustResponse,
)
from app.utils.exceptions import (
    ProductNotFoundException,
    SKUAlreadyExistsException,
    InsufficientStockException,
)


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProductRepository(db)
        self.stock_movement_repo = StockMovementRepository(db)
        self.subcategory_repo = SubcategoryRepository(db)

    # ── Create ────────────────────────────────────────────────────────────

    def create_product(self, data: ProductCreateRequest) -> ProductResponse:
        if self.repo.exists_by_sku(data.sku):
            raise SKUAlreadyExistsException(data.sku)

        if data.subcategory_id:
            subcategory = self.subcategory_repo.get_by_id(data.subcategory_id)
            if not subcategory:
                raise ValueError(f"Subcategory {data.subcategory_id} not found")

        if data.supplier_id:
            supplier = self.db.get(Supplier, data.supplier_id)
            if not supplier or not supplier.is_active:
                raise ValueError(f"Active supplier {data.supplier_id} not found")

        product = self.repo.create(
            name=data.name,
            category=data.category,
            subcategory_id=data.subcategory_id,
            supplier_id=data.supplier_id,
            brand=data.brand,
            model_number=data.model_number,
            sku=data.sku,
            barcode=data.barcode,
            description=data.description,
            price=data.price,
            unit_cost=data.unit_cost,
            quantity=data.quantity,
            minimum_stock=data.minimum_stock,
            reorder_point=data.reorder_point,
            reorder_quantity=data.reorder_quantity,
            image_url=data.image_url,
        )
        return ProductResponse.model_validate(product)

    # ── Read ──────────────────────────────────────────────────────────────

    def get_product(self, product_id: int) -> ProductResponse:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException(product_id)
        return ProductResponse.model_validate(product)

    def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        stock_status: Optional[str] = None,
    ) -> ProductListResponse:
        items, total = self.repo.list_products(
            page, page_size, search, category, category_id, subcategory_id, stock_status
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def list_low_stock(self) -> list[ProductResponse]:
        return [
            ProductResponse.model_validate(p) for p in self.repo.list_low_stock()
        ]

    def list_product_options(self) -> list[ProductOptionResponse]:
        return [
            ProductOptionResponse(
                id=product.id,
                name=product.name,
                sku=product.sku,
                category_id=product.category_id,
                category_name=product.category_name,
                subcategory_id=product.subcategory_id,
                subcategory_name=product.subcategory_name,
                supplier_id=product.supplier_id,
                supplier_name=product.supplier_name,
                price=product.price,
                unit_cost=product.unit_cost,
                quantity=product.quantity,
                reorder_point=product.reorder_point,
                reorder_quantity=product.reorder_quantity,
            )
            for product in self.repo.list_product_options()
        ]

    def catalog_counts(self) -> dict:
        return self.repo.get_catalog_counts()

    # ── Update ────────────────────────────────────────────────────────────

    def update_product(self, product_id: int, data: ProductUpdateRequest) -> ProductResponse:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException(product_id)

        updates = data.model_dump(exclude_none=True)
        if "subcategory_id" in updates:
            subcategory = self.subcategory_repo.get_by_id(updates["subcategory_id"])
            if not subcategory:
                raise ValueError(f"Subcategory {updates['subcategory_id']} not found")
        if "supplier_id" in updates and updates["supplier_id"] is not None:
            supplier = self.db.get(Supplier, updates["supplier_id"])
            if not supplier or not supplier.is_active:
                raise ValueError(f"Active supplier {updates['supplier_id']} not found")
        if updates.get("price"):
            updates["price"] = round(updates["price"], 2)

        updated = self.repo.update(product, **updates)
        return ProductResponse.model_validate(updated)

    # ── Stock Adjustment ──────────────────────────────────────────────────

    def adjust_stock(self, product_id: int, data: StockAdjustRequest) -> StockAdjustResponse:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException(product_id)

        if data.delta < 0 and product.quantity + data.delta < 0:
            raise InsufficientStockException(product.quantity, abs(data.delta))

        previous_qty = product.quantity
        updated = self.repo.adjust_stock(product, data.delta)

        movement_type = "STOCK_IN" if data.delta > 0 else "STOCK_OUT"
        self.stock_movement_repo.create(
            product_id=updated.id,
            warehouse_id=1,
            movement_type=movement_type,
            quantity=abs(data.delta),
            performed_by="system",
            reference=data.reason or f"manual {movement_type.lower()} adjustment",
        )

        # Emit event for future notification service
        event = build_stock_event(
            product_id=updated.id,
            product_name=updated.name,
            sku=updated.sku,
            previous_quantity=previous_qty,
            new_quantity=updated.quantity,
            minimum_stock=updated.minimum_stock,
        )
        emit_stock_event(event)

        return StockAdjustResponse(
            product_id=updated.id,
            previous_quantity=previous_qty,
            new_quantity=updated.quantity,
            delta=data.delta,
            stock_status=updated.stock_status,
            low_stock_alert=updated.is_low_stock or updated.is_out_of_stock,
        )

    # ── Delete ────────────────────────────────────────────────────────────

    def delete_product(self, product_id: int) -> MessageResponse:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundException(product_id)
        self.repo.soft_delete(product)
        return MessageResponse(message=f"Product '{product.name}' deleted successfully")
