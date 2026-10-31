import uuid

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import not_found
from app.modules.orders import service as order_service
from app.modules.orders.schemas import PaymentOrderOut
from app.modules.payments import service
from app.modules.users.models import User

router = APIRouter(tags=["payments"])


@router.post("/orders/{order_id}/payment", response_model=PaymentOrderOut, status_code=201)
async def create_payment(
    order_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id)
    if user.id != order.retailer_id:
        raise not_found("Order not found")
    payment = await service.create_order_payment(db, order)
    await db.commit()
    settings = get_settings()
    return PaymentOrderOut(
        provider=settings.payments_provider,
        gateway_order_id=payment.gateway_order_id or "",
        amount=payment.amount,
        key_id=settings.razorpay_key_id or None,
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    raw = await request.body()
    result = await service.handle_webhook(db, raw, x_razorpay_signature)
    await db.commit()
    return {"status": result}


class DevCaptureIn(BaseModel):
    order_id: uuid.UUID


@router.post("/payments/dev/capture")
async def dev_capture(
    body: DevCaptureIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dev-only: simulate a successful gateway capture when provider=stub."""
    if get_settings().payments_provider != "stub":
        raise not_found("Not found")
    order = await order_service.get_order(db, body.order_id)
    if user.id != order.retailer_id:
        raise not_found("Order not found")
    await service.mark_captured(db, order, gateway_payment_id=f"stub_pay_{order.id.hex[:12]}")
    await db.commit()
    return {"status": "captured"}
