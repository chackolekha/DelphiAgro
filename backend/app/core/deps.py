import uuid
from collections.abc import Awaitable, Callable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError, forbidden
from app.modules.common.enums import Role, UserStatus
from app.modules.users.models import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise AppError("UNAUTHORIZED", "Missing bearer token", 401)
    try:
        from app.core.security import decode_token

        payload = decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", 401) from None
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AppError("UNAUTHORIZED", "User not found", 401)
    if user.status == UserStatus.SUSPENDED:
        raise forbidden("Account suspended")
    return user


def require_role(*roles: Role) -> Callable[..., Awaitable[User]]:
    async def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden("Insufficient role")
        return user

    return dep


async def require_verified(user: User = Depends(get_current_user)) -> User:
    if user.status != UserStatus.VERIFIED:
        raise forbidden("Account not verified. Complete KYC first.")
    return user


async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    return (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
