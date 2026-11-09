"""catalog_and_warehouse_models

Revision ID: 8db0019d36b7
Revises: 2a409b783131
Create Date: 2026-09-11 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8db0019d36b7"
down_revision: Union[str, None] = "2a409b783131"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)

    op.create_table(
        "subcategories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subcategories_category_id"), "subcategories", ["category_id"], unique=False)
    op.create_index(op.f("ix_subcategories_id"), "subcategories", ["id"], unique=False)
    op.create_index(op.f("ix_subcategories_name"), "subcategories", ["name"], unique=False)

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("warehouse_code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("contact_name", sa.String(length=120), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_code"),
    )
    op.create_index(op.f("ix_warehouses_id"), "warehouses", ["id"], unique=False)
    op.create_index(op.f("ix_warehouses_name"), "warehouses", ["name"], unique=False)
    op.create_index(op.f("ix_warehouses_warehouse_code"), "warehouses", ["warehouse_code"], unique=True)

    op.add_column("products", sa.Column("subcategory_id", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("brand", sa.String(length=120), nullable=True))
    op.add_column("products", sa.Column("model_number", sa.String(length=120), nullable=True))
    op.add_column("products", sa.Column("status", sa.String(length=30), nullable=False, server_default="active"))
    op.create_foreign_key(
        "fk_products_subcategory_id_subcategories",
        "products",
        "subcategories",
        ["subcategory_id"],
        ["id"],
    )
    op.create_index(op.f("ix_products_brand"), "products", ["brand"], unique=False)
    op.create_index(op.f("ix_products_model_number"), "products", ["model_number"], unique=False)
    op.create_index(op.f("ix_products_subcategory_id"), "products", ["subcategory_id"], unique=False)

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )
    op.create_index(op.f("ix_inventory_items_id"), "inventory_items", ["id"], unique=False)
    op.create_index(op.f("ix_inventory_items_product_id"), "inventory_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_inventory_items_warehouse_id"), "inventory_items", ["warehouse_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_items_warehouse_id"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_product_id"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_id"), table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index(op.f("ix_products_subcategory_id"), table_name="products")
    op.drop_index(op.f("ix_products_model_number"), table_name="products")
    op.drop_index(op.f("ix_products_brand"), table_name="products")
    op.drop_constraint("fk_products_subcategory_id_subcategories", "products", type_="foreignkey")
    op.drop_column("products", "status")
    op.drop_column("products", "model_number")
    op.drop_column("products", "brand")
    op.drop_column("products", "subcategory_id")

    op.drop_index(op.f("ix_warehouses_warehouse_code"), table_name="warehouses")
    op.drop_index(op.f("ix_warehouses_name"), table_name="warehouses")
    op.drop_index(op.f("ix_warehouses_id"), table_name="warehouses")
    op.drop_table("warehouses")

    op.drop_index(op.f("ix_subcategories_name"), table_name="subcategories")
    op.drop_index(op.f("ix_subcategories_id"), table_name="subcategories")
    op.drop_index(op.f("ix_subcategories_category_id"), table_name="subcategories")
    op.drop_table("subcategories")

    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
