"""electronics catalog constraints

Revision ID: 6c7d8e9f0a12
Revises: 4f2d5f6a7c51
Create Date: 2026-09-15 00:01:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6c7d8e9f0a12"
down_revision: Union[str, None] = "4f2d5f6a7c51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_subcategories_category_name",
        "subcategories",
        ["category_id", "name"],
    )
    op.create_index(
        "ix_products_subcategory_active",
        "products",
        ["subcategory_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_subcategory_active", table_name="products")
    op.drop_constraint(
        "uq_subcategories_category_name",
        "subcategories",
        type_="unique",
    )
