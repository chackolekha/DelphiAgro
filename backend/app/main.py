import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_user_by_phone
from app.core.errors import register_exception_handlers
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.catalogue.router import router as catalogue_router
from app.modules.common.enums import Role, UserStatus
from app.modules.kyc.router import router as kyc_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.users.models import User
from app.modules.users.router import router as users_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.admin_phone:
        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            if await get_user_by_phone(db, settings.admin_phone) is None:
                db.add(
                    User(
                        phone=settings.admin_phone,
                        role=Role.ADMIN,
                        status=UserStatus.VERIFIED,
                        name="Platform Admin",
                    )
                )
                await db.commit()
                log.info("Seeded admin user phone=%s", settings.admin_phone)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="KrishiLink API", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for r in (
        auth_router,
        users_router,
        kyc_router,
        catalogue_router,
        orders_router,
        payments_router,
        notifications_router,
        admin_router,
    ):
        app.include_router(r, prefix="/api/v1")

    @app.get("/health")
    async def health(db: AsyncSession = Depends(get_db)):
        db_ok = False
        try:
            await db.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            log.exception("db health check failed")
        return {"status": "ok" if db_ok else "degraded", "db": db_ok}

    return app


app = create_app()
