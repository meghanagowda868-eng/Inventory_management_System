"""Alembic env.py for Inventory Service."""
import sys, os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.database.session import Base
from app.models.product import Product  # noqa: F401
from app.models.sales_history import SalesHistory, SeasonalEvent  # noqa: F401
from app.models.promotion import Campaign, Offer  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem  # noqa: F401
from app.models.discount_history import FestiveDiscountHistory  # noqa: F401
from app.models.reorder_request import ReorderRequest  # noqa: F401

settings = get_settings()
config = context.config
# Escape % signs for configparser interpolation (e.g., URL-encoded chars like %40)
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
