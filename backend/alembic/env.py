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

# backend 디렉토리를 import 경로에 추가
# env.py는 backend/alembic/ 안에 있어서, 그대로는 models.py를 import 못 함
# parent.parent = backend 폴더
sys.path.append(str(Path(__file__).resolve().parent.parent))

# .env 파일 읽기 (DATABASE_URL_GENERAL 가져오기 위함)
load_dotenv()

# ORM 모델의 metadata 가져오기
from models import BaseGeneral
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ──────────────────────────────────────────
# .env의 DATABASE_URL_GENERAL을 alembic 설정에 동적으로 주입
# alembic.ini의 sqlalchemy.url 라인을 덮어씀 (alembic.ini는 빈 값으로 둘 거임)
# ──────────────────────────────────────────
db_url = os.getenv("DATABASE_URL_GENERAL").replace(
    "postgresql://", "postgresql+asyncpg://"
)
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = BaseGeneral.metadata

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
