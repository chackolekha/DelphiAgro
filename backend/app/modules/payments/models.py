import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.common.enums import PaymentStatus, PaymentType


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("orders.id"), index=True)
    gateway_order_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    gateway_event_id: Mapped[str | None] = mapped_column(sa.String(100), unique=True, nullable=True)
    type: Mapped[PaymentType] = mapped_column(
        sa.Enum(PaymentType, native_enum=False, validate_strings=True)
    )
    status: Mapped[PaymentStatus] = mapped_column(
        sa.Enum(PaymentStatus, native_enum=False, validate_strings=True)
    )
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
