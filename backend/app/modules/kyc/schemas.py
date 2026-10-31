import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.common.enums import KycMethod, ReviewStatus, UserStatus


class KycSubmit(BaseModel):
    """Manual-document / provider-callback submission.

    In the DigiLocker/KUA integration this is populated by the provider callback;
    for the MVP the app collects the document details and an admin reviews them.
    """

    consent: bool = Field(description="Explicit user consent to verification")
    method: KycMethod = KycMethod.MANUAL_DOC
    kyc_name: str = Field(min_length=2, max_length=255)
    kyc_dob: date
    aadhaar_last4: str | None = Field(default=None, min_length=4, max_length=4)
    aadhaar_ref_token: str | None = None
    kyc_photo_s3_key: str | None = None
    provider_txn_id: str | None = None


class KycStatusOut(BaseModel):
    user_status: UserStatus
    review_status: ReviewStatus | None
    reject_reason: str | None
    submitted_at: datetime | None


class KycQueueItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None
    user_phone: str
    user_role: str | None
    method: KycMethod
    kyc_name: str | None
    kyc_dob: date | None
    aadhaar_last4: str | None
    review_status: ReviewStatus
    created_at: datetime


class KycRejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
