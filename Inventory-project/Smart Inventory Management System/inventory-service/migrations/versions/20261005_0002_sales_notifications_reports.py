"""Add sales_orders, sales_order_items, and notifications tables.

Revision ID: a1b2c3d4e5f6
Revises: 9c3d4e5f6a71
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9c3d4e5f6a71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _inspector().has_table(name)


def _has_index(table: str, index: str) -> bool:
    return any(item["name"] == index for item in _inspector().get_indexes(table))


def upgrade() -> None:
    # 1. Create sales_orders table
    if not _has_table("sales_orders"):
        op.create_table(
            "sales_orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("order_number", sa.String(50), nullable=False),
            sa.Column("customer_name", sa.String(120), nullable=False),
            sa.Column("customer_email", sa.String(120), nullable=True),
            sa.Column("customer_phone", sa.String(50), nullable=True),
            sa.Column("channel", sa.String(30), nullable=False, server_default="IN_STORE"),
            sa.Column("payment_method", sa.String(30), nullable=False, server_default="CARD"),
            sa.Column("subtotal", sa.DECIMAL(12, 2), nullable=False, server_default="0.00"),
            sa.Column("discount_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0.00"),
            sa.Column("tax_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0.00"),
            sa.Column("total_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0.00"),
            sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns, is_unique in (
        ("ix_sales_orders_order_number", ["order_number"], True),
        ("ix_sales_orders_status", ["status"], False),
        ("ix_sales_orders_created_at", ["created_at"], False),
    ):
        if not _has_index("sales_orders", index):
            op.create_index(index, "sales_orders", columns, unique=is_unique)

    # 2. Create sales_order_items table
    if not _has_table("sales_order_items"):
        op.create_table(
            "sales_order_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sales_order_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("unit_price", sa.DECIMAL(10, 2), nullable=False),
            sa.Column("unit_cost", sa.DECIMAL(10, 2), nullable=False, server_default="0.00"),
            sa.Column("discount_percent", sa.DECIMAL(5, 2), nullable=False, server_default="0.00"),
            sa.Column("discount_amount", sa.DECIMAL(10, 2), nullable=False, server_default="0.00"),
            sa.Column("line_total", sa.DECIMAL(12, 2), nullable=False),
            sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns in (
        ("ix_sales_order_items_sales_order_id", ["sales_order_id"]),
        ("ix_sales_order_items_product_id", ["product_id"]),
    ):
        if not _has_index("sales_order_items", index):
            op.create_index(index, "sales_order_items", columns)

    # 3. Create notifications table
    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(150), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("category", sa.String(50), nullable=False, server_default="SYSTEM"),
            sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("link_url", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns in (
        ("ix_notifications_user_id", ["user_id"]),
        ("ix_notifications_category", ["category"]),
        ("ix_notifications_is_read", ["is_read"]),
        ("ix_notifications_created_at", ["created_at"]),
    ):
        if not _has_index("notifications", index):
            op.create_index(index, "notifications", columns)


def downgrade() -> None:
    if _has_table("notifications"):
        op.drop_table("notifications")
    if _has_table("sales_order_items"):
        op.drop_table("sales_order_items")
    if _has_table("sales_orders"):
        op.drop_table("sales_orders")
