import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AdminAudit(Base):
    __tablename__ = "admin_audit"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, sa.ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(sa.String(100))
    entity_type: Mapped[str] = mapped_column(sa.String(50))
    entity_id: Mapped[str] = mapped_column(sa.String(50))
    before_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
