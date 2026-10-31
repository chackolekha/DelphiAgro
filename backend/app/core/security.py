import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


def gen_otp(length: int = 6) -> str:
    return f"{secrets.randbelow(10**length):0{length}d}"


def gen_delivery_otp() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def create_access_token(user_id: uuid.UUID, role: str | None) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        "typ": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.access_ttl_min),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algo)


def create_refresh_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "typ": "refresh",
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.refresh_ttl_days),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algo)


def decode_token(token: str, expected_type: str = "access") -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algo])
    if payload.get("typ") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload
