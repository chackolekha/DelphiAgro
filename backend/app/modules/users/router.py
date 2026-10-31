from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.errors import bad_request
from app.modules.common.enums import Role
from app.modules.users import schemas
from app.modules.users.models import PayoutAccount, User

router = APIRouter(tags=["users"])


@router.get("/me", response_model=schemas.UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=schemas.UserOut)
async def update_me(
    body: schemas.ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if "role" in data:
        if user.role is not None and user.role != data["role"]:
            raise bad_request("ROLE_LOCKED", "Role cannot be changed once set")
        if data["role"] == Role.ADMIN:
            raise bad_request("ROLE_LOCKED", "Admin role cannot be self-assigned")
        user.role = data["role"]
    for field in ("name", "district", "state", "pincode", "gstin"):
        if field in data:
            setattr(user, field, data[field])
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/me/payout-account", response_model=schemas.PayoutOut)
async def upsert_payout(
    body: schemas.PayoutIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = (
        await db.execute(select(PayoutAccount).where(PayoutAccount.user_id == user.id))
    ).scalar_one_or_none()
    if acct is None:
        acct = PayoutAccount(user_id=user.id, type=body.type)
        db.add(acct)
    acct.type = body.type
    acct.account_number_enc = body.account_number
    acct.vpa = body.vpa
    acct.ifsc = body.ifsc
    # Penny-drop validation is stubbed; a real gateway call marks it VERIFIED.
    acct.penny_drop_status = "VERIFIED"
    await db.commit()
    await db.refresh(acct)
    return acct


@router.put("/me/push-token", status_code=204)
async def set_push_token(
    body: schemas.PushTokenIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.push_token = body.push_token
    await db.commit()
