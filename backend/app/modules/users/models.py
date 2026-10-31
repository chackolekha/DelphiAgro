import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.common.enums import PayoutType, Role, UserStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    phone: Mapped[str] = mapped_column(sa.String(20), unique=True, index=True)
    role: Mapped[Role | None] = mapped_column(
        sa.Enum(Role, native_enum=False, validate_strings=True), nullable=True
    )
    status: Mapped[UserStatus] = mapped_column(
        sa.Enum(UserStatus, native_enum=False, validate_strings=True),
        default=UserStatus.REGISTERED,
    )
    name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    gstin: Mapped[str | None] = mapped_column(sa.String(15), nullable=True)
    push_token: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class PayoutAccount(Base):
    __tablename__ = "payout_accounts"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[PayoutType] = mapped_column(
        sa.Enum(PayoutType, native_enum=False, validate_strings=True)
    )
    account_number_enc: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    vpa: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    ifsc: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    penny_drop_status: Mapped[str] = mapped_column(sa.String(20), default="PENDING")
    gateway_linked_account_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
