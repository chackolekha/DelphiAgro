import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.common.enums import KycMethod, ReviewStatus


class KycRecord(Base):
    __tablename__ = "kyc_records"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[KycMethod] = mapped_column(
        sa.Enum(KycMethod, native_enum=False, validate_strings=True)
    )
    aadhaar_last4: Mapped[str | None] = mapped_column(sa.String(4), nullable=True)
    aadhaar_ref_token: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)
    kyc_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    kyc_dob: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    kyc_photo_s3_key: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    provider_txn_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        sa.Enum(ReviewStatus, native_enum=False, validate_strings=True),
        default=ReviewStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    consent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
