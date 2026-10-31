"""Scheduled jobs container: same image as the API, different entrypoint.

Runs timeout sweeps and settlement. Single instance only — if replicas are
ever needed, reintroduce a distributed lock here. Usage: python -m app.jobs
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.modules.common.enums import OrderStatus
from app.modules.orders import service as order_service
from app.modules.orders.models import Order

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("jobs")


async def sweep_payment_timeouts() -> None:
    """PLACED orders whose payment window expired → CANCELLED + stock release."""
    cutoff = datetime.now(UTC) - timedelta(minutes=get_settings().payment_window_min)
    async with SessionLocal() as db:
        orders = list(
            (
                await db.execute(
                    select(Order).where(
                        Order.status == OrderStatus.PLACED, Order.created_at < cutoff
                    )
                )
            ).scalars()
        )
        for order in orders:
            await order_service.transition(
                db, order, OrderStatus.CANCELLED, actor_role="SYSTEM", note="payment timeout"
            )
        if orders:
            await db.commit()
            log.info("payment-timeout sweep cancelled %d orders", len(orders))


async def sweep_accept_timeouts() -> None:
    """PAID orders past accept_by → CANCELLED + refund + stock release."""
    async with SessionLocal() as db:
        orders = list(
            (
                await db.execute(
                    select(Order).where(
                        Order.status == OrderStatus.PAID, Order.accept_by < datetime.now(UTC)
                    )
                )
            ).scalars()
        )
        for order in orders:
            await order_service.transition(
                db, order, OrderStatus.CANCELLED, actor_role="SYSTEM", note="accept timeout"
            )
        if orders:
            await db.commit()
            log.info("accept-timeout sweep cancelled %d orders", len(orders))


async def sweep_settlements() -> None:
    """DELIVERED orders past the dispute window → SETTLED + farmer transfer."""
    cutoff = datetime.now(UTC) - timedelta(hours=get_settings().dispute_window_hours)
    async with SessionLocal() as db:
        orders = list(
            (
                await db.execute(
                    select(Order).where(
                        Order.status == OrderStatus.DELIVERED, Order.delivered_at < cutoff
                    )
                )
            ).scalars()
        )
        for order in orders:
            await order_service.transition(
                db, order, OrderStatus.SETTLED, actor_role="SYSTEM", note="auto-settled"
            )
        if orders:
            await db.commit()
            log.info("settlement sweep settled %d orders", len(orders))


async def run_guarded(job) -> None:
    try:
        await job()
    except Exception:
        log.exception("job %s failed", job.__name__)


async def main() -> None:
    scheduler = AsyncIOScheduler()
    for job in (sweep_payment_timeouts, sweep_accept_timeouts, sweep_settlements):
        scheduler.add_job(run_guarded, "interval", minutes=1, args=[job], id=job.__name__)
    scheduler.start()
    log.info("jobs scheduler started")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
