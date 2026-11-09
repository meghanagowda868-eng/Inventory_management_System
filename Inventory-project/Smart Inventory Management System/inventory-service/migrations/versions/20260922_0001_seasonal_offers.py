"""seasonal demand and festive offers

Revision ID: 7a1b2c3d4e5f
Revises: 6c7d8e9f0a12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, None] = "6c7d8e9f0a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seasonal_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("keywords", sa.String(1000), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_seasonal_events_name", "seasonal_events", ["name"], unique=True)

    op.create_table(
        "sales_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("event_name", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_history_product_id", "sales_history", ["product_id"])
    op.create_index("ix_sales_history_sale_date", "sales_history", ["sale_date"])
    op.create_index("ix_sales_history_event_name", "sales_history", ["event_name"])

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("banner_title", sa.String(200), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_campaigns_name", "campaigns", ["name"], unique=True)
    op.create_index("ix_campaigns_starts_at", "campaigns", ["starts_at"])
    op.create_index("ix_campaigns_ends_at", "campaigns", ["ends_at"])

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(20), nullable=False),
        sa.Column("discount_value", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("minimum_purchase", sa.DECIMAL(10, 2), nullable=False, server_default="0"),
        sa.Column("maximum_discount", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_offers_name", "offers", ["name"], unique=True)
    op.create_index("ix_offers_campaign_id", "offers", ["campaign_id"])
    op.create_index("ix_offers_starts_at", "offers", ["starts_at"])
    op.create_index("ix_offers_ends_at", "offers", ["ends_at"])

    op.create_table(
        "offer_products",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("offer_id", "product_id"),
    )
    op.create_table(
        "offer_categories",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("offer_id", "category_id"),
    )
    op.create_table(
        "offer_subcategories",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("subcategory_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subcategory_id"], ["subcategories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("offer_id", "subcategory_id"),
    )


def downgrade() -> None:
    op.drop_table("offer_subcategories")
    op.drop_table("offer_categories")
    op.drop_table("offer_products")
    op.drop_index("ix_offers_ends_at", table_name="offers")
    op.drop_index("ix_offers_starts_at", table_name="offers")
    op.drop_index("ix_offers_campaign_id", table_name="offers")
    op.drop_index("ix_offers_name", table_name="offers")
    op.drop_table("offers")
    op.drop_index("ix_campaigns_ends_at", table_name="campaigns")
    op.drop_index("ix_campaigns_starts_at", table_name="campaigns")
    op.drop_index("ix_campaigns_name", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_sales_history_event_name", table_name="sales_history")
    op.drop_index("ix_sales_history_sale_date", table_name="sales_history")
    op.drop_index("ix_sales_history_product_id", table_name="sales_history")
    op.drop_table("sales_history")
    op.drop_index("ix_seasonal_events_name", table_name="seasonal_events")
    op.drop_table("seasonal_events")
