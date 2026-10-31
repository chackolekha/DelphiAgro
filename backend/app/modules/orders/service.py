import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.modules.catalogue.models import Listing
from app.modules.common.enums import (
    DisputeStatus,
    OrderStatus,
    PaymentStatus,
    PaymentType,
    Role,
)
from app.modules.notifications.service import notify
from app.modules.orders.models import Dispute, Order, OrderEvent, OrderItem
from app.modules.orders.schemas import OrderCreate
from app.modules.payments.models import Payment
from app.modules.users.models import User

TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.ACCEPTED, OrderStatus.REJECTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PACKED, OrderStatus.CANCELLED},
    OrderStatus.PACKED: {OrderStatus.DISPATCHED},
    OrderStatus.DISPATCHED: {OrderStatus.DELIVERED, OrderStatus.DISPUTED},
    OrderStatus.DELIVERED: {OrderStatus.SETTLED, OrderStatus.DISPUTED},
    OrderStatus.DISPUTED: {OrderStatus.SETTLED, OrderStatus.REFUNDED},
}

_COUNTERPARTY_NOTIFY: dict[OrderStatus, str] = {
    OrderStatus.PAID: "Payment received for your order",
    OrderStatus.ACCEPTED: "Your order was accepted by the farmer",
    OrderStatus.REJECTED: "Your order was rejected — refund initiated",
    OrderStatus.PACKED: "Your order is packed",
    OrderStatus.DISPATCHED: "Your order has been dispatched",
    OrderStatus.DELIVERED: "Order delivered",
    OrderStatus.DISPUTED: "A dispute was raised on your order",
    OrderStatus.CANCELLED: "Order cancelled",
    OrderStatus.SETTLED: "Payout released to your account",
    OrderStatus.REFUNDED: "Refund issued to the retailer",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _for_update(db: AsyncSession, stmt):
    """Apply SELECT ... FOR UPDATE only where the dialect supports it."""
    if db.get_bind().dialect.name == "postgresql":
        return stmt.with_for_update()
    return stmt


async def place_order(db: AsyncSession, retailer: User, payload: OrderCreate) -> Order:
    if retailer.role != Role.RETAILER:
        raise forbidden("Only retailers can place orders")

    ids = sorted({str(i.listing_id) for i in payload.items})
    stmt = select(Listing).where(Listing.id.in_([uuid.UUID(i) for i in ids])).order_by(Listing.id)
    listings = {lst.id: lst for lst in (await db.execute(_for_update(db, stmt))).scalars()}

    farmer_id: uuid.UUID | None = None
    total = Decimal("0")
    for item in payload.items:
        listing = listings.get(item.listing_id)
        if listing is None or not listing.active:
            raise not_found(f"Listing {item.listing_id} not found")
        if farmer_id is None:
            farmer_id = listing.farmer_id
        elif listing.farmer_id != farmer_id:
            raise bad_request("MULTI_FARMER", "An order can contain items from one farmer only")
        if item.quantity < listing.min_order_qty:
            raise bad_request(
                "BELOW_MIN_QTY", f"Below minimum order quantity for listing {item.listing_id}"
            )
        if listing.qty_available < item.quantity:
            raise conflict(
                "INSUFFICIENT_STOCK", "Insufficient stock available for one or more items"
            )
        total += listing.price_per_unit * item.quantity

    settings = get_settings()
    fee = (total * Decimal(str(settings.platform_fee_pct))).quantize(Decimal("0.01"))
    order = Order(
        retailer_id=retailer.id,
        farmer_id=farmer_id,
        status=OrderStatus.PLACED,
        total_amount=total,
        platform_fee=fee,
    )
    db.add(order)
    await db.flush()

    for item in payload.items:
        listing = listings[item.listing_id]
        listing.qty_available -= item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                listing_id=item.listing_id,
                quantity=item.quantity,
                price_per_unit=listing.price_per_unit,
                line_total=listing.price_per_unit * item.quantity,
            )
        )
    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.PLACED,
            actor_id=retailer.id,
            actor_role=Role.RETAILER.value,
        )
    )
    assert farmer_id is not None  # guaranteed: items non-empty and validated above
    await notify(db, farmer_id, "New order", f"New order #{str(order.id)[:8]} placed", "order")
    return order


async def get_order(db: AsyncSession, order_id: uuid.UUID) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise not_found("Order not found")
    return order


def assert_party(order: Order, user: User) -> None:
    if user.role == Role.ADMIN:
        return
    if user.id not in (order.retailer_id, order.farmer_id):
        raise forbidden("Not a party to this order")


async def transition(
    db: AsyncSession,
    order: Order,
    to: OrderStatus,
    actor: User | None = None,
    actor_role: str | None = None,
    note: str | None = None,
) -> Order:
    allowed = TRANSITIONS.get(order.status, set())
    if to not in allowed:
        raise conflict(
            "INVALID_TRANSITION", f"Cannot move order from {order.status.value} to {to.value}"
        )

    settings = get_settings()
    was_paid = await _was_paid(db, order.id)
    frm = order.status

    if to == OrderStatus.PAID:
        order.accept_by = _now() + timedelta(hours=settings.accept_window_hours)
    if to == OrderStatus.DELIVERED:
        order.delivered_at = _now()

    if to in (OrderStatus.CANCELLED, OrderStatus.REJECTED):
        await _release_stock(db, order.id)

    if was_paid and to in (OrderStatus.REJECTED, OrderStatus.REFUNDED, OrderStatus.CANCELLED):
        from app.modules.payments.service import create_refund

        await create_refund(db, order)

    if to == OrderStatus.SETTLED:
        from app.modules.payments.service import create_transfer

        await create_transfer(db, order)

    order.status = to
    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=frm,
            to_status=to,
            actor_id=actor.id if actor else None,
            actor_role=actor_role or (actor.role.value if actor and actor.role else None),
            note=note,
        )
    )

    msg = _COUNTERPARTY_NOTIFY.get(to)
    if msg:
        # notify the counterparty (the party that did not act)
        target = order.retailer_id if actor and actor.id == order.farmer_id else order.farmer_id
        if actor is None or actor_role == "SYSTEM":
            target = order.retailer_id
        await notify(db, target, f"Order #{str(order.id)[:8]}", msg, "order")
    return order


async def _was_paid(db: AsyncSession, order_id: uuid.UUID) -> bool:
    row = (
        await db.execute(
            select(Payment.id).where(
                Payment.order_id == order_id,
                Payment.type == PaymentType.CAPTURE,
                Payment.status == PaymentStatus.CAPTURED,
            )
        )
    ).first()
    return row is not None


async def _release_stock(db: AsyncSession, order_id: uuid.UUID) -> None:
    items = list(
        (await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))).scalars()
    )
    for item in items:
        stmt = select(Listing).where(Listing.id == item.listing_id)
        lst = (await db.execute(_for_update(db, stmt))).scalar_one_or_none()
        if lst is not None:
            lst.qty_available += item.quantity


async def open_dispute(db: AsyncSession, order: Order, user: User, reason: str) -> Dispute:
    existing = (
        await db.execute(
            select(Dispute).where(
                Dispute.order_id == order.id, Dispute.status == DisputeStatus.OPEN
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise conflict("DISPUTE_OPEN", "A dispute is already open for this order")
    dispute = Dispute(order_id=order.id, raised_by=user.id, reason=reason)
    db.add(dispute)
    await transition(db, order, OrderStatus.DISPUTED, actor=user, note=reason)
    return dispute


async def order_items_with_listings(db: AsyncSession, order_id: uuid.UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(OrderItem, Listing)
            .join(Listing, Listing.id == OrderItem.listing_id)
            .where(OrderItem.order_id == order_id)
        )
    ).all()
    return [
        {
            "id": it.id,
            "listing_id": it.listing_id,
            "quantity": it.quantity,
            "price_per_unit": it.price_per_unit,
            "line_total": it.line_total,
            "category": lst.category,
            "unit": lst.unit.value,
        }
        for it, lst in rows
    ]
