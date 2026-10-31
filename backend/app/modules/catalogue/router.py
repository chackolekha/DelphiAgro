import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_role, require_verified
from app.core.errors import forbidden, not_found
from app.modules.catalogue import schemas
from app.modules.catalogue.models import Listing
from app.modules.common.enums import Role
from app.modules.users.models import User

router = APIRouter(prefix="/listings", tags=["catalogue"])


@router.get("", response_model=list[schemas.ListingOut])
async def browse(
    category: str | None = None,
    district: str | None = None,
    price_max: Decimal | None = None,
    q: str | None = None,
    farmer_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Listing).order_by(Listing.created_at.desc()).limit(limit).offset(offset)
    if not include_inactive:
        stmt = stmt.where(Listing.active.is_(True))
    if category:
        stmt = stmt.where(Listing.category.ilike(category))
    if district:
        stmt = stmt.where(Listing.district.ilike(district))
    if price_max is not None:
        stmt = stmt.where(Listing.price_per_unit <= price_max)
    if farmer_id:
        stmt = stmt.where(Listing.farmer_id == farmer_id)
    if q:
        stmt = stmt.where(Listing.category.ilike(f"%{q}%") | Listing.variety.ilike(f"%{q}%"))
    return list((await db.execute(stmt)).scalars())


@router.get("/{listing_id}", response_model=schemas.ListingOut)
async def get_listing(listing_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    listing = await db.get(Listing, listing_id)
    if listing is None or not listing.active:
        raise not_found("Listing not found")
    return listing


@router.post("", response_model=schemas.ListingOut, status_code=201)
async def create_listing(
    body: schemas.ListingIn,
    user: User = Depends(require_verified),
    db: AsyncSession = Depends(get_db),
):
    if user.role != Role.FARMER:
        raise forbidden("Only farmers can create listings")
    listing = Listing(farmer_id=user.id, **body.model_dump())
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.put("/{listing_id}", response_model=schemas.ListingOut)
async def update_listing(
    listing_id: uuid.UUID,
    body: schemas.ListingIn,
    user: User = Depends(require_role(Role.FARMER)),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise not_found("Listing not found")
    if listing.farmer_id != user.id:
        raise forbidden("Not your listing")
    for k, v in body.model_dump().items():
        setattr(listing, k, v)
    await db.commit()
    await db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=204)
async def deactivate_listing(
    listing_id: uuid.UUID,
    user: User = Depends(require_role(Role.FARMER)),
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise not_found("Listing not found")
    if listing.farmer_id != user.id:
        raise forbidden("Not your listing")
    listing.active = False
    await db.commit()
