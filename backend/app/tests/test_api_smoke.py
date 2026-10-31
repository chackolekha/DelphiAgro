"""End-to-end smoke test: OTP login → KYC → listing → order → pay → deliver.

Runs against the real FastAPI app over httpx ASGITransport with SQLite +
in-memory TTL store — no external services needed.
"""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base, get_db
from app.core.kv import TTLStore, get_kv
from app.main import app
from app.modules.common.enums import Role, UserStatus
from app.modules.users.models import User


@pytest.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    store = TTLStore()

    async def _db():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_kv] = lambda: store

    # seed an admin directly (lifespan doesn't run under ASGITransport)
    async with maker() as s:
        s.add(
            User(phone="+911111111111", role=Role.ADMIN, status=UserStatus.VERIFIED, name="Admin")
        )
        await s.commit()

    async with httpx.ASGITransport(app=app) as transport:
        yield httpx.AsyncClient(transport=transport, base_url="http://test")

    app.dependency_overrides.clear()
    await engine.dispose()


async def signup(client: httpx.AsyncClient, phone: str) -> str:
    res = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert res.status_code == 202
    otp = res.json()["dev_otp"]
    res = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert res.status_code == 200
    return res.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def verify_user(client: httpx.AsyncClient, admin: str, phone: str, role: str) -> str:
    token = await signup(client, phone)
    await client.put("/api/v1/me", json={"name": f"Test {role}", "role": role}, headers=auth(token))
    res = await client.post(
        "/api/v1/kyc/submit",
        json={
            "consent": True,
            "method": "MANUAL_DOC",
            "kyc_name": f"Test {role}",
            "kyc_dob": "1990-01-01",
        },
        headers=auth(token),
    )
    assert res.status_code == 201
    # admin approves from the KYC queue
    res = await client.get("/api/v1/admin/kyc?status=PENDING", headers=auth(admin))
    kyc_id = next(k["id"] for k in res.json() if k["user_phone"] == phone)
    res = await client.post(f"/api/v1/admin/kyc/{kyc_id}/approve", headers=auth(admin))
    assert res.status_code == 204
    return token


async def test_full_order_lifecycle(client: httpx.AsyncClient):
    admin = await signup(client, "+911111111111")
    farmer = await verify_user(client, admin, "+919000000001", "FARMER")
    retailer = await verify_user(client, admin, "+919000000002", "RETAILER")

    # farmer lists produce
    res = await client.post(
        "/api/v1/listings",
        json={
            "category": "Potato",
            "variety": "Pukhraj",
            "unit": "KG",
            "price_per_unit": "25",
            "qty_available": "100",
            "min_order_qty": "5",
            "district": "Pune",
        },
        headers=auth(farmer),
    )
    assert res.status_code == 201
    listing_id = res.json()["id"]

    # retailer browses and orders
    res = await client.get("/api/v1/listings?district=Pune", headers=auth(retailer))
    assert any(lst["id"] == listing_id for lst in res.json())
    res = await client.post(
        "/api/v1/orders",
        json={"items": [{"listing_id": listing_id, "quantity": "10"}]},
        headers={**auth(retailer), "Idempotency-Key": "smoke-1"},
    )
    assert res.status_code == 201
    order_id = res.json()["order"]["id"]
    assert res.json()["order"]["status"] == "PLACED"

    # pay via stub gateway
    res = await client.post(f"/api/v1/orders/{order_id}/payment", headers=auth(retailer))
    assert res.status_code == 201
    res = await client.post(
        "/api/v1/payments/dev/capture", json={"order_id": order_id}, headers=auth(retailer)
    )
    assert res.status_code == 200

    # farmer fulfils
    for step in ("accept", "pack"):
        res = await client.post(f"/api/v1/orders/{order_id}/{step}", headers=auth(farmer))
        assert res.status_code == 200
    res = await client.post(
        f"/api/v1/orders/{order_id}/dispatch",
        json={"vehicle_no": "MH12AB1234", "driver_phone": "+919999900000"},
        headers=auth(farmer),
    )
    assert res.status_code == 200

    # retailer sees delivery OTP, farmer enters it
    res = await client.get(f"/api/v1/orders/{order_id}", headers=auth(retailer))
    otp = res.json()["delivery_otp"]
    assert otp and len(otp) == 4
    res = await client.post(
        f"/api/v1/orders/{order_id}/deliver", json={"otp": otp}, headers=auth(farmer)
    )
    assert res.status_code == 200
    assert res.json()["order"]["status"] == "DELIVERED"

    # stock stayed reserved; timeline is complete
    res = await client.get(f"/api/v1/listings/{listing_id}")
    assert res.json()["qty_available"] == "90.00"
    res = await client.get(f"/api/v1/orders/{order_id}", headers=auth(retailer))
    statuses = [e["to_status"] for e in res.json()["events"]]
    assert statuses == ["PLACED", "PAID", "ACCEPTED", "PACKED", "DISPATCHED", "DELIVERED"]


async def test_unverified_cannot_order(client: httpx.AsyncClient):
    admin = await signup(client, "+911111111111")
    farmer = await verify_user(client, admin, "+919000000003", "FARMER")
    res = await client.post(
        "/api/v1/listings",
        json={
            "category": "Onion",
            "unit": "KG",
            "price_per_unit": "30",
            "qty_available": "50",
            "min_order_qty": "1",
        },
        headers=auth(farmer),
    )
    listing_id = res.json()["id"]

    unverified = await signup(client, "+919000000004")
    res = await client.post(
        "/api/v1/orders",
        json={"items": [{"listing_id": listing_id, "quantity": "5"}]},
        headers=auth(unverified),
    )
    assert res.status_code == 403
