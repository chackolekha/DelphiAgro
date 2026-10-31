import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.common.enums import ListingUnit


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        sa.CheckConstraint("qty_available >= 0", name="ck_listings_qty"),
        sa.CheckConstraint("price_per_unit > 0", name="ck_listings_price"),
        sa.Index("ix_listings_search", "category", "district", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(sa.String(100))
    variety: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    grade: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    unit: Mapped[ListingUnit] = mapped_column(
        sa.Enum(ListingUnit, native_enum=False, validate_strings=True)
    )
    price_per_unit: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))
    qty_available: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2))
    min_order_qty: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=Decimal("1"))
    district: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    pickup_location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    photo_keys: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    harvest_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
