from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.modules.common.enums import OrderStatus, PaymentStatus, PaymentType, Role, UserStatus
from app.modules.orders import service
from app.modules.orders.schemas import OrderCreate, OrderItemIn
from app.modules.payments import service as payment_service
from app.modules.payments.models import Payment
from app.tests.conftest import make_listing, make_user


async def test_place_order_reserves_stock(session):
    farmer = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    listing = await make_listing(session, farmer, qty=Decimal("100"))

    order = await service.place_order(
        session,
        retailer,
        OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
    )
    await session.commit()
    await session.refresh(listing)

    assert order.status == OrderStatus.PLACED
    assert listing.qty_available == Decimal("90")
    assert order.total_amount == Decimal("250.00")


async def test_place_order_rejects_insufficient_stock(session):
    farmer = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    listing = await make_listing(session, farmer, qty=Decimal("5"))

    with pytest.raises(AppError) as exc:
        await service.place_order(
            session,
            retailer,
            OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
        )
    assert exc.value.code == "INSUFFICIENT_STOCK"


async def test_place_order_rejects_multi_farmer(session):
    f1 = await make_user(session, Role.FARMER)
    f2 = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    l1 = await make_listing(session, f1)
    l2 = await make_listing(session, f2)

    with pytest.raises(AppError) as exc:
        await service.place_order(
            session,
            retailer,
            OrderCreate(
                items=[
                    OrderItemIn(listing_id=l1.id, quantity=Decimal("10")),
                    OrderItemIn(listing_id=l2.id, quantity=Decimal("10")),
                ]
            ),
        )
    assert exc.value.code == "MULTI_FARMER"


async def test_unverified_retailer_cannot_order(session):
    # enforcement is at the dependency level; service also guards role
    farmer = await make_user(session, Role.FARMER)
    not_retailer = await make_user(session, Role.FARMER, status=UserStatus.VERIFIED)
    listing = await make_listing(session, farmer)

    with pytest.raises(AppError):
        await service.place_order(
            session,
            not_retailer,
            OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
        )


async def test_full_lifecycle_and_settlement(session):
    farmer = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    listing = await make_listing(session, farmer, qty=Decimal("50"))

    order = await service.place_order(
        session,
        retailer,
        OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
    )
    await session.flush()

    # pay → PAID
    await payment_service.create_order_payment(session, order)
    await payment_service.mark_captured(session, order, "pay_test", "evt_test")
    assert order.status == OrderStatus.PAID

    await service.transition(session, order, OrderStatus.ACCEPTED, actor=farmer)
    await service.transition(session, order, OrderStatus.PACKED, actor=farmer)
    await service.transition(session, order, OrderStatus.DISPATCHED, actor=farmer)
    await service.transition(session, order, OrderStatus.DELIVERED, actor=retailer)
    await service.transition(session, order, OrderStatus.SETTLED, actor_role="SYSTEM")
    await session.commit()

    assert order.status == OrderStatus.SETTLED
    payments = list(
        (await session.execute(select(Payment).where(Payment.order_id == order.id))).scalars()
    )
    transfer = next(p for p in payments if p.type == PaymentType.TRANSFER)
    assert transfer.amount == order.total_amount - order.platform_fee
    # stock stays reserved after settlement
    await session.refresh(listing)
    assert listing.qty_available == Decimal("40")


async def test_reject_releases_stock_and_refunds(session):
    farmer = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    listing = await make_listing(session, farmer, qty=Decimal("50"))

    order = await service.place_order(
        session,
        retailer,
        OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
    )
    await session.flush()
    await payment_service.create_order_payment(session, order)
    await payment_service.mark_captured(session, order, "pay_x", "evt_x")

    await service.transition(session, order, OrderStatus.REJECTED, actor=farmer, note="no stock")
    await session.commit()

    await session.refresh(listing)
    assert listing.qty_available == Decimal("50")
    refunds = list(
        (
            await session.execute(
                select(Payment).where(
                    Payment.order_id == order.id, Payment.type == PaymentType.REFUND
                )
            )
        ).scalars()
    )
    assert len(refunds) == 1 and refunds[0].status == PaymentStatus.PROCESSED


async def test_illegal_transition_rejected(session):
    farmer = await make_user(session, Role.FARMER)
    retailer = await make_user(session, Role.RETAILER)
    listing = await make_listing(session, farmer)
    order = await service.place_order(
        session,
        retailer,
        OrderCreate(items=[OrderItemIn(listing_id=listing.id, quantity=Decimal("10"))]),
    )
    with pytest.raises(AppError) as exc:
        await service.transition(session, order, OrderStatus.DELIVERED, actor=farmer)
    assert exc.value.code == "INVALID_TRANSITION"
