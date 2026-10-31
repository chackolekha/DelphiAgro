import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_role
from app.core.errors import bad_request, conflict, not_found
from app.modules.admin import service
from app.modules.admin.models import AdminAudit
from app.modules.common.enums import (
    DisputeResolution,
    DisputeStatus,
    OrderStatus,
    ReviewStatus,
    Role,
    UserStatus,
)
from app.modules.kyc.models import KycRecord
from app.modules.kyc.schemas import KycQueueItem, KycRejectIn
from app.modules.notifications.service import notify
from app.modules.orders import service as order_service
from app.modules.orders.models import Dispute, Order
from app.modules.orders.schemas import OrderOut, ResolveDisputeIn
from app.modules.users.models import User
from app.modules.users.schemas import UserOut

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_role(Role.ADMIN))]
)


@router.get("/kyc", response_model=list[KycQueueItem])
async def kyc_queue(
    status: ReviewStatus = ReviewStatus.PENDING,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(KycRecord, User)
            .join(User, User.id == KycRecord.user_id)
            .where(KycRecord.review_status == status)
            .order_by(KycRecord.created_at)
        )
    ).all()
    return [
        KycQueueItem(
            id=k.id,
            user_id=k.user_id,
            user_name=u.name,
            user_phone=u.phone,
            user_role=u.role.value if u.role else None,
            method=k.method,
            kyc_name=k.kyc_name,
            kyc_dob=k.kyc_dob,
            aadhaar_last4=k.aadhaar_last4,
            review_status=k.review_status,
            created_at=k.created_at,
        )
        for k, u in rows
    ]


@router.post("/kyc/{kyc_id}/approve", status_code=204)
async def approve_kyc(
    kyc_id: uuid.UUID,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(KycRecord, kyc_id)
    if record is None:
        raise not_found("KYC record not found")
    if record.review_status != ReviewStatus.PENDING:
        raise conflict("ALREADY_REVIEWED", "KYC record already reviewed")
    user = await db.get(User, record.user_id)
    if user is None:
        raise not_found("User not found")
    record.review_status = ReviewStatus.APPROVED
    record.reviewed_by = admin.id
    record.reviewed_at = datetime.now(UTC)
    user.status = UserStatus.VERIFIED
    await service.audit(
        db,
        admin,
        "KYC_APPROVE",
        "kyc_record",
        str(kyc_id),
        before={"user_status": UserStatus.REGISTERED.value},
        after={"user_status": UserStatus.VERIFIED.value},
    )
    await notify(db, user.id, "Verification approved", "Your account is now verified.", "kyc")
    await db.commit()


@router.post("/kyc/{kyc_id}/reject", status_code=204)
async def reject_kyc(
    kyc_id: uuid.UUID,
    body: KycRejectIn,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(KycRecord, kyc_id)
    if record is None:
        raise not_found("KYC record not found")
    if record.review_status != ReviewStatus.PENDING:
        raise conflict("ALREADY_REVIEWED", "KYC record already reviewed")
    user = await db.get(User, record.user_id)
    if user is None:
        raise not_found("User not found")
    record.review_status = ReviewStatus.REJECTED
    record.reviewed_by = admin.id
    record.reviewed_at = datetime.now(UTC)
    record.reject_reason = body.reason
    user.status = UserStatus.REJECTED
    await service.audit(
        db, admin, "KYC_REJECT", "kyc_record", str(kyc_id), after={"reason": body.reason}
    )
    await notify(db, user.id, "Verification rejected", f"Reason: {body.reason}", "kyc")
    await db.commit()


@router.post("/users/{user_id}/suspend", status_code=204)
async def suspend_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User not found")
    if user.role == Role.ADMIN:
        raise bad_request("CANNOT_SUSPEND_ADMIN", "Cannot suspend an admin")
    await service.audit(
        db,
        admin,
        "USER_SUSPEND",
        "user",
        str(user_id),
        before={"status": user.status.value},
        after={"status": UserStatus.SUSPENDED.value},
    )
    user.status = UserStatus.SUSPENDED
    await db.commit()


@router.post("/users/{user_id}/reactivate", status_code=204)
async def reactivate_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise not_found("User not found")
    await service.audit(
        db,
        admin,
        "USER_REACTIVATE",
        "user",
        str(user_id),
        before={"status": user.status.value},
        after={"status": UserStatus.VERIFIED.value},
    )
    user.status = UserStatus.VERIFIED
    await db.commit()


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(
    status: OrderStatus | None = None,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Order.status == status)
    return list((await db.execute(stmt)).scalars())


@router.get("/disputes")
async def list_disputes(
    status: DisputeStatus = DisputeStatus.OPEN,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Dispute).where(Dispute.status == status).order_by(Dispute.created_at)
        )
    ).scalars()
    return [
        {
            "id": str(d.id),
            "order_id": str(d.order_id),
            "raised_by": str(d.raised_by),
            "reason": d.reason,
            "status": d.status.value,
            "created_at": d.created_at,
        }
        for d in rows
    ]


@router.post("/disputes/{dispute_id}/resolve", status_code=204)
async def resolve_dispute(
    dispute_id: uuid.UUID,
    body: ResolveDisputeIn,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    dispute = await db.get(Dispute, dispute_id)
    if dispute is None:
        raise not_found("Dispute not found")
    if dispute.status != DisputeStatus.OPEN:
        raise conflict("ALREADY_RESOLVED", "Dispute already resolved")
    order = await order_service.get_order(db, dispute.order_id)
    target = (
        OrderStatus.SETTLED
        if body.resolution == DisputeResolution.RELEASE
        else OrderStatus.REFUNDED
    )
    await order_service.transition(
        db,
        order,
        target,
        actor=admin,
        actor_role="ADMIN",
        note=f"dispute resolved: {body.resolution.value}",
    )
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolution = body.resolution
    dispute.resolved_by = admin.id
    dispute.resolved_at = datetime.now(UTC)
    await service.audit(
        db,
        admin,
        "DISPUTE_RESOLVE",
        "dispute",
        str(dispute_id),
        after={"resolution": body.resolution.value},
    )
    await db.commit()


@router.get("/audit")
async def audit_log(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(select(AdminAudit).order_by(AdminAudit.created_at.desc()).limit(limit))
    ).scalars()
    return [
        {
            "id": str(a.id),
            "admin_id": str(a.admin_id),
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "before": a.before_json,
            "after": a.after_json,
            "created_at": a.created_at,
        }
        for a in rows
    ]


@router.get("/users", response_model=list[UserOut])
async def list_users(
    status: UserStatus | None = None,
    role: Role | None = None,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(User.status == status)
    if role:
        stmt = stmt.where(User.role == role)
    return list((await db.execute(stmt)).scalars())
