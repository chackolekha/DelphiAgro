import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.common.enums import DisputeResolution, DisputeStatus, OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"), index=True)
    farmer_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        sa.Enum(OrderStatus, native_enum=False, validate_strings=True),
        default=OrderStatus.PLACED,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))
    platform_fee: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))
    delivery_otp: Mapped[str | None] = mapped_column(sa.String(4), nullable=True)
    accept_by: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    vehicle_no: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    driver_phone: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), index=True
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (sa.CheckConstraint("quantity > 0", name="ck_order_items_qty"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("listings.id"))
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2))
    price_per_unit: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(
        sa.Enum(OrderStatus, native_enum=False, validate_strings=True), nullable=True
    )
    to_status: Mapped[OrderStatus] = mapped_column(
        sa.Enum(OrderStatus, native_enum=False, validate_strings=True)
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, nullable=True)
    actor_role: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class Dispute(Base):
    __tablename__ = "disputes"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("orders.id"), index=True)
    raised_by: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(sa.String(1000))
    status: Mapped[DisputeStatus] = mapped_column(
        sa.Enum(DisputeStatus, native_enum=False, validate_strings=True),
        default=DisputeStatus.OPEN,
    )
    resolution: Mapped[DisputeResolution | None] = mapped_column(
        sa.Enum(DisputeResolution, native_enum=False, validate_strings=True), nullable=True
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
