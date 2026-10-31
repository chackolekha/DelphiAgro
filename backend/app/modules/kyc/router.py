from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import bad_request, conflict
from app.modules.common.enums import UserStatus
from app.modules.kyc import schemas
from app.modules.kyc.models import KycRecord
from app.modules.users.models import User

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/submit", response_model=schemas.KycStatusOut, status_code=201)
async def submit_kyc(
    body: schemas.KycSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.consent:
        raise bad_request("CONSENT_REQUIRED", "Consent is required for verification")
    if user.status == UserStatus.VERIFIED:
        raise conflict("ALREADY_VERIFIED", "Account already verified")

    record = KycRecord(
        user_id=user.id,
        method=body.method,
        kyc_name=body.kyc_name,
        kyc_dob=body.kyc_dob,
        aadhaar_last4=body.aadhaar_last4,
        aadhaar_ref_token=body.aadhaar_ref_token,
        kyc_photo_s3_key=body.kyc_photo_s3_key,
        provider_txn_id=body.provider_txn_id,
        consent_at=datetime.now(UTC),
    )
    db.add(record)
    user.status = UserStatus.KYC_SUBMITTED
    await db.commit()
    return schemas.KycStatusOut(
        user_status=user.status,
        review_status=record.review_status,
        reject_reason=None,
        submitted_at=record.created_at,
    )


@router.get("/status", response_model=schemas.KycStatusOut)
async def kyc_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    record = (
        await db.execute(
            select(KycRecord)
            .where(KycRecord.user_id == user.id)
            .order_by(KycRecord.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return schemas.KycStatusOut(
        user_status=user.status,
        review_status=record.review_status if record else None,
        reject_reason=record.reject_reason if record else None,
        submitted_at=record.created_at if record else None,
    )
