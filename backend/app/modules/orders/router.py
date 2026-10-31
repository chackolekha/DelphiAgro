import uuid

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_verified
from app.core.errors import bad_request, forbidden
from app.core.redis_client import get_redis
from app.core.security import gen_delivery_otp
from app.modules.common.enums import OrderStatus, Role
from app.modules.orders import schemas, service
from app.modules.orders.models import OrderEvent
from app.modules.payments.models import Payment
from app.modules.users.models import User

router = APIRouter(prefix="/orders", tags=["orders"])


async def _detail(db: AsyncSession, order, user: User) -> schemas.OrderDetailOut:
    items = await service.order_items_with_listings(db, order.id)
    events = list(
        (
            await db.execute(
                select(OrderEvent)
                .where(OrderEvent.order_id == order.id)
                .order_by(OrderEvent.created_at)
            )
        ).scalars()
    )
    payments = list(
        (
            await db.execute(
                select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at)
            )
        ).scalars()
    )
    otp = order.delivery_otp if user.id == order.retailer_id else None
    return schemas.OrderDetailOut(
        order=schemas.OrderOut.model_validate(order),
        items=[schemas.OrderItemOut(**i) for i in items],
        events=[schemas.EventOut.model_validate(e) for e in events],
        payments=[schemas.PaymentOut.model_validate(p) for p in payments],
        delivery_otp=otp,
    )


@router.post("", response_model=schemas.OrderDetailOut, status_code=201)
async def place(
    body: schemas.OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    idem = f"idem:orders:{user.id}:{idempotency_key}" if idempotency_key else None
    if idem:
        existing = await r.get(idem)
        if existing:
            order = await service.get_order(db, uuid.UUID(str(existing)))
            return await _detail(db, order, user)

    order = await service.place_order(db, user, body)
    order.delivery_otp = gen_delivery_otp()
    # payment window is implicit: jobs sweep PLACED orders older than payment_window_min
    await db.commit()
    if idem:
        await r.set(idem, str(order.id), ex=86400)
    return await _detail(db, order, user)


@router.get("", response_model=list[schemas.OrderOut])
async def list_orders(
    status: OrderStatus | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(service.Order).order_by(service.Order.created_at.desc())
    if user.role == Role.FARMER:
        stmt = stmt.where(service.Order.farmer_id == user.id)
    elif user.role == Role.RETAILER:
        stmt = stmt.where(service.Order.retailer_id == user.id)
    elif user.role != Role.ADMIN:
        raise forbidden("Set a role first")
    if status:
        stmt = stmt.where(service.Order.status == status)
    return list((await db.execute(stmt)).scalars())


@router.get("/{order_id}", response_model=schemas.OrderDetailOut)
async def detail(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await service.get_order(db, order_id)
    service.assert_party(order, user)
    return await _detail(db, order, user)


def _require_farmer(order, user: User) -> None:
    if user.id != order.farmer_id:
        raise forbidden("Only the order's farmer can do this")


def _require_retailer(order, user: User) -> None:
    if user.id != order.retailer_id:
        raise forbidden("Only the order's retailer can do this")


async def _party_order(order_id: uuid.UUID, user: User, db: AsyncSession):
    order = await service.get_order(db, order_id)
    service.assert_party(order, user)
    return order


@router.post("/{order_id}/accept", response_model=schemas.OrderDetailOut)
async def accept(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    order = await _party_order(order_id, user, db)
    _require_farmer(order, user)
    await service.transition(db, order, OrderStatus.ACCEPTED, actor=user)
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/reject", response_model=schemas.OrderDetailOut)
async def reject(
    order_id: uuid.UUID,
    body: schemas.ReasonIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _party_order(order_id, user, db)
    _require_farmer(order, user)
    await service.transition(
        db, order, OrderStatus.REJECTED, actor=user, note=body.reason if body else None
    )
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/pack", response_model=schemas.OrderDetailOut)
async def pack(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    order = await _party_order(order_id, user, db)
    _require_farmer(order, user)
    await service.transition(db, order, OrderStatus.PACKED, actor=user)
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/dispatch", response_model=schemas.OrderDetailOut)
async def dispatch(
    order_id: uuid.UUID,
    body: schemas.DispatchIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _party_order(order_id, user, db)
    _require_farmer(order, user)
    order.vehicle_no = body.vehicle_no
    order.driver_phone = body.driver_phone
    await service.transition(db, order, OrderStatus.DISPATCHED, actor=user)
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/deliver", response_model=schemas.OrderDetailOut)
async def deliver(
    order_id: uuid.UUID,
    body: schemas.DeliverIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _party_order(order_id, user, db)
    otp = body.otp if body else None
    if user.id == order.farmer_id:
        if not otp or otp != order.delivery_otp:
            raise bad_request("INVALID_OTP", "Delivery OTP does not match")
    elif user.id == order.retailer_id:
        pass  # retailer "Received" fallback — no OTP needed
    else:
        raise forbidden("Not a party to this order")
    await service.transition(db, order, OrderStatus.DELIVERED, actor=user)
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/cancel", response_model=schemas.OrderDetailOut)
async def cancel(
    order_id: uuid.UUID,
    body: schemas.ReasonIn | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _party_order(order_id, user, db)
    await service.transition(
        db, order, OrderStatus.CANCELLED, actor=user, note=body.reason if body else None
    )
    await db.commit()
    return await _detail(db, order, user)


@router.post("/{order_id}/dispute", response_model=schemas.OrderDetailOut, status_code=201)
async def dispute(
    order_id: uuid.UUID,
    body: schemas.DisputeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _party_order(order_id, user, db)
    _require_retailer(order, user)
    await service.open_dispute(db, order, user, body.reason)
    await db.commit()
    return await _detail(db, order, user)
