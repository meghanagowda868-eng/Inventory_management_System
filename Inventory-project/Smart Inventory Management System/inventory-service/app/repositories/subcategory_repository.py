"""Repository for product subcategories."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.subcategory import Subcategory


class SubcategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Subcategory]:
        return self.db.query(Subcategory).order_by(Subcategory.name).all()

    def get_by_id(self, subcategory_id: int) -> Optional[Subcategory]:
        return self.db.query(Subcategory).filter(Subcategory.id == subcategory_id).first()

    def list_by_category(self, category_id: int) -> list[Subcategory]:
        return (
            self.db.query(Subcategory)
            .filter(Subcategory.category_id == category_id)
            .order_by(Subcategory.name)
            .all()
        )

    def exists_in_category(self, category_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Subcategory.id).filter(
            Subcategory.category_id == category_id,
            Subcategory.name == name.strip(),
        )
        if exclude_id is not None:
            query = query.filter(Subcategory.id != exclude_id)
        return query.first() is not None

    def create(self, category_id: int, name: str, description: Optional[str] = None) -> Subcategory:
        subcategory = Subcategory(category_id=category_id, name=name.strip(), description=description)
        self.db.add(subcategory)
        self.db.commit()
        self.db.refresh(subcategory)
        return subcategory

    def update(self, subcategory: Subcategory, **kwargs) -> Subcategory:
        for field, value in kwargs.items():
            if hasattr(subcategory, field) and value is not None:
                setattr(subcategory, field, value)
        self.db.commit()
        self.db.refresh(subcategory)
        return subcategory

    def delete(self, subcategory: Subcategory) -> None:
        self.db.delete(subcategory)
        self.db.commit()
