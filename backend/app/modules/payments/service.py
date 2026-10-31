import hashlib
import hmac
import uuid
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, bad_request, conflict
from app.modules.common.enums import (
    OrderStatus,
    PaymentStatus,
    PaymentType,
)
from app.modules.orders.models import Order
from app.modules.payments.models import Payment


class Gateway:
    """Payment gateway abstraction. `stub` executes instantly for dev."""

    name = "stub"

    async def create_order(self, amount: Decimal) -> str:
        return f"stub_order_{uuid.uuid4().hex[:16]}"

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return True


class RazorpayGateway(Gateway):
    name = "razorpay"

    def __init__(self) -> None:
        s = get_settings()
        self.key_id = s.razorpay_key_id
        self.key_secret = s.razorpay_key_secret
        self.webhook_secret = s.razorpay_webhook_secret

    async def create_order(self, amount: Decimal) -> str:
        async with httpx.AsyncClient(auth=(self.key_id, self.key_secret), timeout=15) as client:
            resp = await client.post(
                "https://api.razorpay.com/v1/orders",
                json={"amount": int(amount * 100), "currency": "INR"},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature or not self.webhook_secret:
            return False
        expected = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def get_gateway() -> Gateway:
    if get_settings().payments_provider == "razorpay":
        return RazorpayGateway()
    return Gateway()


async def create_order_payment(db: AsyncSession, order: Order) -> Payment:
    """Create a gateway order + a CAPTURE/CREATED payment row for checkout."""
    if order.status != OrderStatus.PLACED:
        raise conflict("NOT_PAYABLE", f"Order is {order.status.value}, cannot pay")
    existing = (
        await db.execute(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.type == PaymentType.CAPTURE,
                Payment.status.in_([PaymentStatus.CREATED, PaymentStatus.CAPTURED]),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    gw = get_gateway()
    gateway_order_id = await gw.create_order(order.total_amount)
    payment = Payment(
        order_id=order.id,
        gateway_order_id=gateway_order_id,
        type=PaymentType.CAPTURE,
        status=PaymentStatus.CREATED,
        amount=order.total_amount,
    )
    db.add(payment)
    await db.flush()
    return payment


async def mark_captured(
    db: AsyncSession,
    order: Order,
    gateway_payment_id: str | None = None,
    gateway_event_id: str | None = None,
) -> Payment:
    """Webhook/dev path: mark the CAPTURE payment captured and move PLACED→PAID."""
    from app.modules.orders import service as order_service

    payment = (
        await db.execute(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.type == PaymentType.CAPTURE,
                Payment.status == PaymentStatus.CREATED,
            )
        )
    ).scalar_one_or_none()
    if payment is None:
        raise conflict("NO_PENDING_PAYMENT", "No pending payment for this order")
    payment.status = PaymentStatus.CAPTURED
    payment.gateway_payment_id = gateway_payment_id
    payment.gateway_event_id = gateway_event_id or f"evt_{uuid.uuid4().hex[:16]}"
    await order_service.transition(db, order, OrderStatus.PAID, actor_role="SYSTEM")
    return payment


async def create_refund(db: AsyncSession, order: Order) -> Payment:
    capture = (
        await db.execute(
            select(Payment).where(
                Payment.order_id == order.id,
                Payment.type == PaymentType.CAPTURE,
                Payment.status == PaymentStatus.CAPTURED,
            )
        )
    ).scalar_one_or_none()
    if capture is None:
        raise bad_request("NOT_PAID", "Order has no captured payment to refund")
    # Stub provider refunds instantly; real gateway call goes here.
    refund = Payment(
        order_id=order.id,
        gateway_payment_id=capture.gateway_payment_id,
        type=PaymentType.REFUND,
        status=PaymentStatus.PROCESSED,
        amount=order.total_amount,
    )
    db.add(refund)
    return refund


async def create_transfer(db: AsyncSession, order: Order) -> Payment:
    farmer_amount = order.total_amount - order.platform_fee
    transfer = Payment(
        order_id=order.id,
        type=PaymentType.TRANSFER,
        status=PaymentStatus.PROCESSED,  # stub; Route transfer call goes here
        amount=farmer_amount,
    )
    db.add(transfer)
    return transfer


async def handle_webhook(db: AsyncSession, raw_body: bytes, signature: str | None) -> str:
    """Razorpay webhook entry point. Returns a short status string."""
    gw = get_gateway()
    if not gw.verify_webhook_signature(raw_body, signature):
        raise AppError("BAD_SIGNATURE", "Invalid webhook signature", 400)

    import json

    event = json.loads(raw_body)
    event_id = event.get("id") or event.get("event")
    if not event_id:
        raise bad_request("BAD_EVENT", "Missing event id")

    # Idempotency: a row with this gateway_event_id already processed → skip.
    dup = (await db.execute(select(Payment.id).where(Payment.gateway_event_id == event_id))).first()
    if dup:
        return "duplicate"

    name = event.get("event")
    entity = (event.get("payload") or {}).get("payment", {}).get("entity", {})
    gateway_order_id = entity.get("order_id")
    if not gateway_order_id:
        return "ignored"

    payment = (
        await db.execute(
            select(Payment).where(
                Payment.gateway_order_id == gateway_order_id,
                Payment.type == PaymentType.CAPTURE,
            )
        )
    ).scalar_one_or_none()
    if payment is None:
        return "unknown_order"

    order = await db.get(Order, payment.order_id)
    if order is None:
        return "unknown_order"
    if name == "payment.captured" and order.status == OrderStatus.PLACED:
        await mark_captured(db, order, entity.get("id"), event_id)
        return "captured"
    if name == "payment.failed":
        payment.status = PaymentStatus.FAILED
        payment.gateway_event_id = event_id
        return "failed"
    return "ignored"
