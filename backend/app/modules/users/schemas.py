import uuid

from pydantic import BaseModel, Field

from app.modules.common.enums import PayoutType, Role, UserStatus


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    role: Role | None
    status: UserStatus
    name: str | None
    district: str | None
    state: str | None
    pincode: str | None
    gstin: str | None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    gstin: str | None = None


class PayoutIn(BaseModel):
    type: PayoutType
    account_number: str | None = Field(default=None, max_length=34)
    vpa: str | None = Field(default=None, max_length=100)
    ifsc: str | None = Field(default=None, max_length=20)


class PayoutOut(BaseModel):
    id: uuid.UUID
    type: PayoutType
    vpa: str | None
    ifsc: str | None
    penny_drop_status: str

    model_config = {"from_attributes": True}


class PushTokenIn(BaseModel):
    push_token: str = Field(max_length=255)
