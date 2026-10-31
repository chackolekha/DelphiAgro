from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_url = get_settings().database_url
# Neon pooler runs PgBouncer transaction-pooling, which breaks asyncpg's
# per-connection prepared-statement cache — disable it for Postgres URLs.
_connect_args = {"statement_cache_size": 0} if _url.startswith("postgres") else {}

engine = create_async_engine(
    _url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_connect_args,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
