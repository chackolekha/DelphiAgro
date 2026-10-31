import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.common.enums import ListingUnit


class ListingIn(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    variety: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    unit: ListingUnit
    price_per_unit: Decimal = Field(gt=0)
    qty_available: Decimal = Field(ge=0)
    min_order_qty: Decimal = Field(default=Decimal("1"), gt=0)
    district: str | None = Field(default=None, max_length=100)
    pickup_location: str | None = Field(default=None, max_length=255)
    photo_keys: list[str] | None = Field(default=None, max_length=3)
    harvest_date: date | None = None


class ListingOut(ListingIn):
    id: uuid.UUID
    farmer_id: uuid.UUID
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
