import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification

log = logging.getLogger(__name__)


async def notify(
    db: AsyncSession, user_id: uuid.UUID, title: str, body: str, ntype: str = "info"
) -> None:
    db.add(Notification(user_id=user_id, title=title, body=body, type=ntype))
    # Push (FCM) + SMS senders are stubbed — wire real providers in Phase 2.
    log.info("notify user=%s type=%s title=%s", user_id, ntype, title)
