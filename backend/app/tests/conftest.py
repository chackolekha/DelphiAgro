import os
import uuid
from decimal import Decimal

# Point the app at an in-memory SQLite DB before any app imports.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["PAYMENTS_PROVIDER"] = "stub"

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.modules.catalogue.models import Listing
from app.modules.common.enums import ListingUnit, Role, UserStatus
from app.modules.users.models import User


@pytest.fixture
async def session():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def make_user(session: AsyncSession, role: Role, status=UserStatus.VERIFIED) -> User:
    user = User(
        phone=f"+91{uuid.uuid4().int % 10**10:010d}",
        role=role,
        status=status,
        name=role.value.title(),
    )
    session.add(user)
    await session.flush()
    return user


async def make_listing(
    session: AsyncSession,
    farmer: User,
    qty: Decimal = Decimal("100"),
    price: Decimal = Decimal("25"),
) -> Listing:
    listing = Listing(
        farmer_id=farmer.id,
        category="Potato",
        variety="Pukhraj",
        unit=ListingUnit.KG,
        price_per_unit=price,
        qty_available=qty,
        min_order_qty=Decimal("5"),
        district="Pune",
        active=True,
    )
    session.add(listing)
    await session.flush()
    return listing
