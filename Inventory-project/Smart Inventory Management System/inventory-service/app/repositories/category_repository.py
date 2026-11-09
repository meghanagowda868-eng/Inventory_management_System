"""Repository for catalog categories."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Category]:
        return self.db.query(Category).order_by(Category.name).all()

    def get_by_id(self, category_id: int) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.name == name.strip()).first()

    def exists_by_name(self, name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Category.id).filter(Category.name == name.strip())
        if exclude_id is not None:
            query = query.filter(Category.id != exclude_id)
        return query.first() is not None

    def create(self, name: str, description: Optional[str] = None) -> Category:
        category = Category(name=name.strip(), description=description)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category: Category, **kwargs) -> Category:
        for field, value in kwargs.items():
            if hasattr(category, field) and value is not None:
                setattr(category, field, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.commit()
