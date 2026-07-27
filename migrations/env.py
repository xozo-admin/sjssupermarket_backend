from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database.base import Base
from app.modules.catalog.category_model import Category  # noqa: F401
from app.modules.catalog.management_models import Brand, Product, Tax, Unit, Variation  # noqa: F401
from app.modules.auth.model import User  # noqa: F401
from app.modules.customers.address_model import CustomerAddress  # noqa: F401
from app.modules.orders.models import Order, OrderItem  # noqa: F401
from app.modules.refunds.models import RefundConfiguration, RefundRequest  # noqa: F401
from app.modules.notifications.models import PushDevice  # noqa: F401
from app.modules.customers.wishlist_model import WishlistItem  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
