"""baseline schema (all MVP tables)

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-31

Creates the full MVP schema from SQLAlchemy metadata. Subsequent changes must be
explicit, backward-compatible migrations (per BLUEPRINT §9.2).
"""

from alembic import op

from app.core.db import Base

import app.modules.users.models  # noqa: F401
import app.modules.kyc.models  # noqa: F401
import app.modules.catalogue.models  # noqa: F401
import app.modules.orders.models  # noqa: F401
import app.modules.payments.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.admin.models  # noqa: F401

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
