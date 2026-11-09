"""Add reorder settings, reorder requests, supplier updates, and purchase order workflow enhancements.

Revision ID: 9c3d4e5f6a71
Revises: 8b2c3d4e5f60
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9c3d4e5f6a71"
down_revision: Union[str, None] = "8b2c3d4e5f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_column(table: str, column: str) -> bool:
    return any(item["name"] == column for item in _inspector().get_columns(table))


def _has_index(table: str, index: str) -> bool:
    return any(item["name"] == index for item in _inspector().get_indexes(table))


def _has_foreign_key(table: str, constraint: str) -> bool:
    return any(item["name"] == constraint for item in _inspector().get_foreign_keys(table))


def upgrade() -> None:
    # 1. Update suppliers table
    if _has_table("suppliers"):
        if not _has_column("suppliers", "address"):
            op.add_column("suppliers", sa.Column("address", sa.String(255), nullable=True))
        if not _has_column("suppliers", "status"):
            op.add_column("suppliers", sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"))
        if not _has_column("suppliers", "updated_at"):
            op.add_column(
                "suppliers",
                sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            )

    # 2. Update products table
    if _has_table("products"):
        if not _has_column("products", "reorder_point"):
            op.add_column("products", sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="10"))
        if not _has_column("products", "reorder_quantity"):
            op.add_column("products", sa.Column("reorder_quantity", sa.Integer(), nullable=False, server_default="20"))
        if not _has_column("products", "supplier_id"):
            op.add_column("products", sa.Column("supplier_id", sa.Integer(), nullable=True))
        if not _has_index("products", "ix_products_supplier_id"):
            op.create_index("ix_products_supplier_id", "products", ["supplier_id"])
        if not _has_foreign_key("products", "fk_products_supplier_id_suppliers"):
            op.create_foreign_key(
                "fk_products_supplier_id_suppliers", "products", "suppliers",
                ["supplier_id"], ["id"],
            )

    # 3. Create reorder_requests table
    if not _has_table("reorder_requests"):
        op.create_table(
            "reorder_requests",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("supplier_id", sa.Integer(), nullable=True),
            sa.Column("requested_quantity", sa.Integer(), nullable=False),
            sa.Column("reorder_reason", sa.Text(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("requested_by", sa.Integer(), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns in (
        ("ix_reorder_requests_product_id", ["product_id"]),
        ("ix_reorder_requests_supplier_id", ["supplier_id"]),
        ("ix_reorder_requests_status", ["status"]),
    ):
        if not _has_index("reorder_requests", index):
            op.create_index(index, "reorder_requests", columns)

    # 4. Update purchase_orders table
    if _has_table("purchase_orders"):
        if not _has_column("purchase_orders", "po_number"):
            op.add_column("purchase_orders", sa.Column("po_number", sa.String(50), nullable=True))
            # Backfill any existing purchase orders
            bind = op.get_bind()
            bind.execute(sa.text(
                "UPDATE purchase_orders SET po_number = CONCAT('PO-2026-', LPAD(id, 4, '0')) WHERE po_number IS NULL"
            ))
            op.alter_column("purchase_orders", "po_number", existing_type=sa.String(50), nullable=False)
        if not _has_index("purchase_orders", "ix_purchase_orders_po_number"):
            op.create_index("ix_purchase_orders_po_number", "purchase_orders", ["po_number"], unique=True)
        if not _has_column("purchase_orders", "reorder_request_id"):
            op.add_column("purchase_orders", sa.Column("reorder_request_id", sa.Integer(), nullable=True))
        if not _has_index("purchase_orders", "ix_purchase_orders_reorder_request_id"):
            op.create_index("ix_purchase_orders_reorder_request_id", "purchase_orders", ["reorder_request_id"])
        if not _has_foreign_key("purchase_orders", "fk_purchase_orders_reorder_request_id"):
            op.create_foreign_key(
                "fk_purchase_orders_reorder_request_id", "purchase_orders", "reorder_requests",
                ["reorder_request_id"], ["id"], ondelete="SET NULL",
            )


def downgrade() -> None:
    if _has_table("purchase_orders"):
        if _has_foreign_key("purchase_orders", "fk_purchase_orders_reorder_request_id"):
            op.drop_constraint("fk_purchase_orders_reorder_request_id", "purchase_orders", type_="foreignkey")
        if _has_index("purchase_orders", "ix_purchase_orders_reorder_request_id"):
            op.drop_index("ix_purchase_orders_reorder_request_id", table_name="purchase_orders")
        if _has_column("purchase_orders", "reorder_request_id"):
            op.drop_column("purchase_orders", "reorder_request_id")
        if _has_index("purchase_orders", "ix_purchase_orders_po_number"):
            op.drop_index("ix_purchase_orders_po_number", table_name="purchase_orders")
        if _has_column("purchase_orders", "po_number"):
            op.drop_column("purchase_orders", "po_number")

    if _has_table("reorder_requests"):
        op.drop_table("reorder_requests")

    if _has_table("products"):
        if _has_foreign_key("products", "fk_products_supplier_id_suppliers"):
            op.drop_constraint("fk_products_supplier_id_suppliers", "products", type_="foreignkey")
        if _has_index("products", "ix_products_supplier_id"):
            op.drop_index("ix_products_supplier_id", table_name="products")
        if _has_column("products", "supplier_id"):
            op.drop_column("products", "supplier_id")
        if _has_column("products", "reorder_quantity"):
            op.drop_column("products", "reorder_quantity")
        if _has_column("products", "reorder_point"):
            op.drop_column("products", "reorder_point")

    if _has_table("suppliers"):
        if _has_column("suppliers", "updated_at"):
            op.drop_column("suppliers", "updated_at")
        if _has_column("suppliers", "status"):
            op.drop_column("suppliers", "status")
        if _has_column("suppliers", "address"):
            op.drop_column("suppliers", "address")
