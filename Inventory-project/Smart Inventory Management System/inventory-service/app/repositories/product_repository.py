"""
Product Repository — all DB queries for the Inventory Service.
"""
from typing import Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.subcategory import Subcategory
from app.models.category import Category
from app.models.supplier import Supplier


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(Product.id == product_id, Product.is_active == True)  # noqa: E712
            .first()
        )

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(Product.sku == sku.upper(), Product.is_active == True)  # noqa: E712
            .first()
        )

    def exists_by_sku(self, sku: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Product.id).filter(Product.sku == sku.upper())
        if exclude_id:
            q = q.filter(Product.id != exclude_id)
        return q.first() is not None

    def list_products(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        stock_status: Optional[str] = None,   # available | low_stock | out_of_stock
    ) -> tuple[list[Product], int]:
        """Return paginated products with optional filters."""
        q = (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(Product.is_active == True)  # noqa: E712
        )
        q = q.outerjoin(Product.subcategory).outerjoin(Subcategory.category).outerjoin(Product.supplier)

        if search:
            pattern = f"%{search}%"
            q = q.filter(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.category.ilike(pattern),
                    Category.name.ilike(pattern),
                    Subcategory.name.ilike(pattern),
                    Supplier.name.ilike(pattern),
                )
            )

        if category:
            q = q.filter(Category.name.ilike(f"%{category}%"))

        if category_id:
            q = q.filter(Category.id == category_id)

        if subcategory_id:
            q = q.filter(Product.subcategory_id == subcategory_id)

        if stock_status == "out_of_stock":
            q = q.filter(Product.quantity == 0)
        elif stock_status == "low_stock":
            q = q.filter(Product.quantity > 0, Product.quantity < Product.minimum_stock)
        elif stock_status == "available":
            q = q.filter(Product.quantity >= Product.minimum_stock)

        total = q.count()
        items = q.order_by(Product.name).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_low_stock(self) -> list[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(
                Product.is_active == True,  # noqa: E712
                Product.quantity > 0,
                Product.quantity < Product.minimum_stock,
            )
            .order_by(Product.quantity)
            .all()
        )

    def list_product_options(self) -> list[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(Product.is_active.is_(True))
            .order_by(Product.name)
            .all()
        )

    def list_out_of_stock(self) -> list[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.supplier),
                joinedload(Product.subcategory).joinedload(Subcategory.category),
            )
            .filter(Product.is_active == True, Product.quantity == 0)  # noqa: E712
            .all()
        )

    def create(self, **kwargs) -> Product:
        product = Product(**kwargs)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return self.get_by_id(product.id) or product

    def update(self, product: Product, **kwargs) -> Product:
        for field, value in kwargs.items():
            if hasattr(product, field) and value is not None:
                setattr(product, field, value)
        self.db.commit()
        self.db.refresh(product)
        return self.get_by_id(product.id) or product

    def adjust_stock(self, product: Product, delta: int) -> Product:
        product.quantity = max(0, product.quantity + delta)
        self.db.commit()
        self.db.refresh(product)
        return self.get_by_id(product.id) or product

    def soft_delete(self, product: Product) -> None:
        product.is_active = False
        self.db.commit()

    def get_stats(self) -> dict:
        """Aggregate stats used by AI service."""
        total_products = self.db.query(func.count(Product.id)).filter(
            Product.is_active == True  # noqa: E712
        ).scalar()

        total_value = self.db.query(
            func.sum(Product.price * Product.quantity)
        ).filter(Product.is_active == True).scalar() or 0  # noqa: E712

        low_stock_count = self.db.query(func.count(Product.id)).filter(
            Product.is_active == True,  # noqa: E712
            Product.quantity > 0,
            Product.quantity < Product.minimum_stock,
        ).scalar()

        out_of_stock_count = self.db.query(func.count(Product.id)).filter(
            Product.is_active == True, Product.quantity == 0  # noqa: E712
        ).scalar()

        return {
            "total_products": total_products,
            "total_inventory_value": float(total_value),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
        }

    def get_catalog_counts(self) -> dict:
        rows = (
            self.db.query(Category.name, Subcategory.name, func.count(Product.id))
            .outerjoin(Subcategory, Subcategory.category_id == Category.id)
            .outerjoin(Product, Product.subcategory_id == Subcategory.id)
            .filter((Product.is_active == True) | (Product.id.is_(None)))  # noqa: E712
            .group_by(Category.name, Subcategory.name)
            .all()
        )
        categories: dict[str, int] = {}
        subcategories: dict[str, int] = {}
        for category_name, subcategory_name, count in rows:
            categories[category_name] = categories.get(category_name, 0) + count
            if subcategory_name:
                subcategories[subcategory_name] = count
        return {"categories": categories, "subcategories": subcategories}
