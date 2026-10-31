import uuid

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_user_by_phone
from app.core.errors import AppError, bad_request
from app.core.kv import TTLStore
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    gen_otp,
)
from app.modules.users.models import User

OTP_KEY = "otp:{}"
OTP_ATTEMPTS_KEY = "otp_attempts:{}"
OTP_RATE_KEY = "otp_rate:{}"


async def request_otp(r: TTLStore, phone: str) -> str | None:
    """Generate and store an OTP. Returns it only in dev-echo mode."""
    settings = get_settings()
    rate_key = OTP_RATE_KEY.format(phone)
    count = await r.incr(rate_key)
    if count == 1:
        await r.expire(rate_key, 3600)
    if count > settings.otp_rate_limit_per_hour:
        raise AppError("RATE_LIMITED", "Too many OTP requests. Try later.", 429)

    otp = gen_otp()
    await r.set(OTP_KEY.format(phone), otp, ex=settings.otp_ttl_sec)
    await r.delete(OTP_ATTEMPTS_KEY.format(phone))
    # TODO: send via SMS gateway (MSG91 / AWS SNS, DLT template)
    return otp if settings.otp_dev_echo else None


async def verify_otp(db: AsyncSession, r: TTLStore, phone: str, otp: str) -> User:
    settings = get_settings()
    attempts_key = OTP_ATTEMPTS_KEY.format(phone)
    attempts = int(await r.get(attempts_key) or 0)
    if attempts >= settings.otp_max_attempts:
        raise AppError("RATE_LIMITED", "Too many attempts. Request a new OTP.", 429)

    stored = await r.get(OTP_KEY.format(phone))
    if stored is None or stored != otp:
        await r.incr(attempts_key)
        await r.expire(attempts_key, settings.otp_ttl_sec)
        raise bad_request("INVALID_OTP", "Invalid or expired OTP")

    await r.delete(OTP_KEY.format(phone), attempts_key)
    user = await get_user_by_phone(db, phone)
    if user is None:
        user = User(phone=phone)
        db.add(user)
        await db.flush()
    return user


def issue_tokens(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role.value if user.role else None),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.PyJWTError:
        raise AppError("UNAUTHORIZED", "Invalid refresh token", 401) from None
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AppError("UNAUTHORIZED", "User not found", 401)
    return issue_tokens(user)
