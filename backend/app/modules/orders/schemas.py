import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.common.enums import DisputeResolution, OrderStatus, PaymentStatus, PaymentType


class OrderItemIn(BaseModel):
    listing_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1, max_length=20)


class OrderItemOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    quantity: Decimal
    price_per_unit: Decimal
    line_total: Decimal
    category: str | None = None
    unit: str | None = None


class OrderOut(BaseModel):
    id: uuid.UUID
    retailer_id: uuid.UUID
    farmer_id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    platform_fee: Decimal
    accept_by: datetime | None
    vehicle_no: str | None
    driver_phone: str | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: uuid.UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    actor_role: str | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: uuid.UUID
    type: PaymentType
    status: PaymentStatus
    amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailOut(BaseModel):
    order: OrderOut
    items: list[OrderItemOut]
    events: list[EventOut]
    payments: list[PaymentOut]
    delivery_otp: str | None = None


class DispatchIn(BaseModel):
    vehicle_no: str | None = Field(default=None, max_length=20)
    driver_phone: str | None = Field(default=None, max_length=20)


class DeliverIn(BaseModel):
    otp: str | None = Field(default=None, min_length=4, max_length=4)


class ReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ResolveDisputeIn(BaseModel):
    resolution: DisputeResolution


class PaymentOrderOut(BaseModel):
    provider: str
    gateway_order_id: str
    amount: Decimal
    currency: str = "INR"
    key_id: str | None = None
