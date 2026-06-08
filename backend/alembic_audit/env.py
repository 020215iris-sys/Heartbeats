import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))
load_dotenv()

from models import BaseAudit

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ──────────────────────────────────────────
# 옵션 B Phase 3: alembic 마이그레이션은 OWNER 계정(heartbeat)으로 실행
# - 백엔드 트래픽은 audit_writer(INSERT/SELECT만) 사용, 마이그레이션은 OWNER
# - audit DB는 특히 audit_writer가 DDL/UPDATE/DELETE 권한이 없어서
#   ADMIN URL 없이는 마이그레이션 자체가 불가능
# ──────────────────────────────────────────
admin_url = os.getenv("ADMIN_DATABASE_URL_AUDIT")
if not admin_url:
    raise RuntimeError(
        "ADMIN_DATABASE_URL_AUDIT 환경변수가 없습니다. "
        "alembic 마이그레이션은 OWNER(heartbeat) 계정으로 실행돼야 합니다. "
        "backend/.env에서 ADMIN_DATABASE_URL_AUDIT 확인하세요."
    )
db_url = admin_url.replace("postgresql://", "postgresql+asyncpg://")
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = BaseAudit.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()