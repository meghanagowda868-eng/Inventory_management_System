"""Add supplier and manager-confirmed purchase-order tables.

Revision ID: 8b2c3d4e5f60
Revises: 7a1b2c3d4e5f
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8b2c3d4e5f60"
down_revision: Union[str, None] = "7a1b2c3d4e5f"
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
    if not _has_column("products", "unit_cost"):
        op.add_column("products", sa.Column("unit_cost", sa.DECIMAL(10, 2), nullable=True))
    for column, type_ in (
        ("festival_event_id", sa.Integer()),
        ("minimum_discount", sa.DECIMAL(5, 2)),
        ("maximum_discount", sa.DECIMAL(5, 2)),
        ("selected_discount", sa.DECIMAL(5, 2)),
    ):
        if not _has_column("campaigns", column):
            op.add_column("campaigns", sa.Column(column, type_, nullable=True))
    if not _has_foreign_key("campaigns", "fk_campaigns_festival_event_id_seasonal_events"):
        op.create_foreign_key(
            "fk_campaigns_festival_event_id_seasonal_events", "campaigns", "seasonal_events",
            ["festival_event_id"], ["id"],
        )
    if not _has_index("campaigns", "ix_campaigns_festival_event_id"):
        op.create_index("ix_campaigns_festival_event_id", "campaigns", ["festival_event_id"])

    if not _has_table("suppliers"):
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("contact_name", sa.String(120), nullable=True),
            sa.Column("email", sa.String(180), nullable=True),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("suppliers", "ix_suppliers_name"):
        op.create_index("ix_suppliers_name", "suppliers", ["name"])

    if not _has_table("purchase_orders"):
        op.create_table(
            "purchase_orders",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("supplier_id", sa.Integer(), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING_APPROVAL"),
            sa.Column("order_date", sa.Date(), nullable=False),
            sa.Column("expected_delivery", sa.Date(), nullable=True),
            sa.Column("total_amount", sa.DECIMAL(12, 2), nullable=False, server_default="0.00"),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("approved_by", sa.Integer(), nullable=True),
            sa.Column("received_by", sa.Integer(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns in (
        ("ix_purchase_orders_supplier_id", ["supplier_id"]),
        ("ix_purchase_orders_warehouse_id", ["warehouse_id"]),
        ("ix_purchase_orders_status", ["status"]),
    ):
        if not _has_index("purchase_orders", index):
            op.create_index(index, "purchase_orders", columns)

    if not _has_table("purchase_order_items"):
        op.create_table(
            "purchase_order_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("purchase_order_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("unit_cost", sa.DECIMAL(10, 2), nullable=False),
            sa.Column("total_cost", sa.DECIMAL(12, 2), nullable=False),
            sa.Column("received_quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("purchase_order_id", "product_id", name="uq_purchase_order_product"),
        )
    for index, columns in (
        ("ix_purchase_order_items_purchase_order_id", ["purchase_order_id"]),
        ("ix_purchase_order_items_product_id", ["product_id"]),
    ):
        if not _has_index("purchase_order_items", index):
            op.create_index(index, "purchase_order_items", columns)

    if not _has_table("festive_discount_history"):
        op.create_table(
            "festive_discount_history",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("festival_event_id", sa.Integer(), nullable=False),
            sa.Column("campaign_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("discount_percent", sa.DECIMAL(5, 2), nullable=False),
            sa.Column("units_sold", sa.Integer(), nullable=False),
            sa.Column("revenue", sa.DECIMAL(12, 2), nullable=False),
            sa.Column("profit", sa.DECIMAL(12, 2), nullable=True),
            sa.Column("campaign_date", sa.Date(), nullable=False),
            sa.Column("recorded_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["festival_event_id"], ["seasonal_events.id"]),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    for index, columns in (
        ("ix_festive_discount_history_festival_event_id", ["festival_event_id"]),
        ("ix_festive_discount_history_campaign_id", ["campaign_id"]),
        ("ix_festive_discount_history_product_id", ["product_id"]),
        ("ix_festive_discount_history_campaign_date", ["campaign_date"]),
    ):
        if not _has_index("festive_discount_history", index):
            op.create_index(index, "festive_discount_history", columns)


def downgrade() -> None:
    op.drop_index("ix_festive_discount_history_campaign_date", table_name="festive_discount_history")
    op.drop_index("ix_festive_discount_history_product_id", table_name="festive_discount_history")
    op.drop_index("ix_festive_discount_history_campaign_id", table_name="festive_discount_history")
    op.drop_index("ix_festive_discount_history_festival_event_id", table_name="festive_discount_history")
    op.drop_table("festive_discount_history")
    op.drop_index("ix_purchase_order_items_product_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_purchase_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")
    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_warehouse_id", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_campaigns_festival_event_id", table_name="campaigns")
    op.drop_constraint("fk_campaigns_festival_event_id_seasonal_events", "campaigns", type_="foreignkey")
    op.drop_column("campaigns", "selected_discount")
    op.drop_column("campaigns", "maximum_discount")
    op.drop_column("campaigns", "minimum_discount")
    op.drop_column("campaigns", "festival_event_id")
    op.drop_column("products", "unit_cost")