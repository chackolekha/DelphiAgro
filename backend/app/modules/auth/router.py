import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import forbidden
from app.core.redis_client import get_redis
from app.modules.auth import schemas, service
from app.modules.common.enums import UserStatus
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/otp/request", response_model=schemas.OtpRequestOut, status_code=202)
async def otp_request(body: schemas.OtpRequest, r: redis.Redis = Depends(get_redis)):
    dev_otp = await service.request_otp(r, body.phone)
    return schemas.OtpRequestOut(dev_otp=dev_otp)


@router.post("/otp/verify")
async def otp_verify(
    body: schemas.OtpVerify,
    db: AsyncSession = Depends(get_db),
    r: redis.Redis = Depends(get_redis),
):
    user = await service.verify_otp(db, r, body.phone, body.otp)
    if user.status == UserStatus.SUSPENDED:
        raise forbidden("Account suspended")
    await db.commit()
    return {**service.issue_tokens(user), "user": UserOut.model_validate(user)}


@router.post("/refresh", response_model=schemas.TokenPair)
async def refresh(body: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await service.refresh_tokens(db, body.refresh_token)
