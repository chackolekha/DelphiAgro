from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.models import AdminAudit
from app.modules.users.models import User


async def audit(
    db: AsyncSession,
    admin: User,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AdminAudit(
            admin_id=admin.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=before,
            after_json=after,
        )
    )
