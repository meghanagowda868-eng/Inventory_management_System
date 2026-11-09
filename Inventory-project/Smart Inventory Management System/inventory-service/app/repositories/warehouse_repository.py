"""Repository for warehouses."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse


class WarehouseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Warehouse]:
        return self.db.query(Warehouse).order_by(Warehouse.name).all()

    def get_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        return self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    def get_by_code(self, warehouse_code: str) -> Optional[Warehouse]:
        return self.db.query(Warehouse).filter(Warehouse.warehouse_code == warehouse_code.strip().upper()).first()

    def exists_by_code(self, warehouse_code: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Warehouse.id).filter(Warehouse.warehouse_code == warehouse_code.strip().upper())
        if exclude_id is not None:
            query = query.filter(Warehouse.id != exclude_id)
        return query.first() is not None

    def create(self, **kwargs) -> Warehouse:
        warehouse = Warehouse(**kwargs)
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def update(self, warehouse: Warehouse, **kwargs) -> Warehouse:
        for field, value in kwargs.items():
            if hasattr(warehouse, field) and value is not None:
                setattr(warehouse, field, value)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def delete(self, warehouse: Warehouse) -> None:
        self.db.delete(warehouse)
        self.db.commit()
