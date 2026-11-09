"""Service logic for catalog and warehouse entities."""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.category_repository import CategoryRepository
from app.repositories.subcategory_repository import SubcategoryRepository
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.category import CategoryCreateRequest, CategoryResponse, CategoryUpdateRequest
from app.schemas.subcategory import (
    SubcategoryCreateRequest,
    SubcategoryResponse,
    SubcategoryUpdateRequest,
)
from app.schemas.warehouse import WarehouseCreateRequest, WarehouseResponse, WarehouseUpdateRequest


class CatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.category_repo = CategoryRepository(db)
        self.subcategory_repo = SubcategoryRepository(db)
        self.warehouse_repo = WarehouseRepository(db)

    # Categories
    def list_categories(self) -> list[CategoryResponse]:
        items = self.category_repo.get_all()
        return [CategoryResponse.model_validate(item) for item in items]

    def create_category(self, data: CategoryCreateRequest) -> CategoryResponse:
        if self.category_repo.exists_by_name(data.name):
            raise ValueError(f"Category '{data.name}' already exists")
        item = self.category_repo.create(data.name, data.description)
        return CategoryResponse.model_validate(item)

    def update_category(self, category_id: int, data: CategoryUpdateRequest) -> CategoryResponse:
        item = self.category_repo.get_by_id(category_id)
        if not item:
            raise ValueError(f"Category {category_id} not found")
        if data.name and self.category_repo.exists_by_name(data.name, category_id):
            raise ValueError(f"Category '{data.name}' already exists")
        updated = self.category_repo.update(item, **data.model_dump(exclude_none=True))
        return CategoryResponse.model_validate(updated)

    def delete_category(self, category_id: int) -> None:
        item = self.category_repo.get_by_id(category_id)
        if not item:
            raise ValueError(f"Category {category_id} not found")
        self.category_repo.delete(item)

    # Subcategories
    def list_subcategories(self, category_id: Optional[int] = None) -> list[SubcategoryResponse]:
        if category_id is not None:
            items = self.subcategory_repo.list_by_category(category_id)
        else:
            items = self.subcategory_repo.get_all()
        return [SubcategoryResponse.model_validate(item) for item in items]

    def create_subcategory(self, data: SubcategoryCreateRequest) -> SubcategoryResponse:
        if self.subcategory_repo.exists_in_category(data.category_id, data.name):
            raise ValueError(f"Subcategory '{data.name}' already exists in this category")
        item = self.subcategory_repo.create(data.category_id, data.name, data.description)
        return SubcategoryResponse.model_validate(item)

    def update_subcategory(self, subcategory_id: int, data: SubcategoryUpdateRequest) -> SubcategoryResponse:
        item = self.subcategory_repo.get_by_id(subcategory_id)
        if not item:
            raise ValueError(f"Subcategory {subcategory_id} not found")
        if data.name and self.subcategory_repo.exists_in_category(item.category_id, data.name, subcategory_id):
            raise ValueError(f"Subcategory '{data.name}' already exists in this category")
        updated = self.subcategory_repo.update(item, **data.model_dump(exclude_none=True))
        return SubcategoryResponse.model_validate(updated)

    def delete_subcategory(self, subcategory_id: int) -> None:
        item = self.subcategory_repo.get_by_id(subcategory_id)
        if not item:
            raise ValueError(f"Subcategory {subcategory_id} not found")
        self.subcategory_repo.delete(item)

    # Warehouses
    def list_warehouses(self) -> list[WarehouseResponse]:
        items = self.warehouse_repo.get_all()
        return [WarehouseResponse.model_validate(item) for item in items]

    def create_warehouse(self, data: WarehouseCreateRequest) -> WarehouseResponse:
        if self.warehouse_repo.exists_by_code(data.warehouse_code):
            raise ValueError(f"Warehouse code '{data.warehouse_code}' already exists")
        item = self.warehouse_repo.create(**data.model_dump())
        return WarehouseResponse.model_validate(item)

    def update_warehouse(self, warehouse_id: int, data: WarehouseUpdateRequest) -> WarehouseResponse:
        item = self.warehouse_repo.get_by_id(warehouse_id)
        if not item:
            raise ValueError(f"Warehouse {warehouse_id} not found")
        if data.warehouse_code and self.warehouse_repo.exists_by_code(data.warehouse_code, warehouse_id):
            raise ValueError(f"Warehouse code '{data.warehouse_code}' already exists")
        updated = self.warehouse_repo.update(item, **data.model_dump(exclude_none=True))
        return WarehouseResponse.model_validate(updated)

    def delete_warehouse(self, warehouse_id: int) -> None:
        item = self.warehouse_repo.get_by_id(warehouse_id)
        if not item:
            raise ValueError(f"Warehouse {warehouse_id} not found")
        self.warehouse_repo.delete(item)
