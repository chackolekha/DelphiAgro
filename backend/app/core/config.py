from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/krishilink"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algo: str = "HS256"
    access_ttl_min: int = 15
    refresh_ttl_days: int = 30

    otp_ttl_sec: int = 300
    otp_dev_echo: bool = True
    otp_max_attempts: int = 5
    otp_rate_limit_per_hour: int = 10

    # Dev-demo only: tokenless requests act as a seeded verified retailer.
    # MUST be false in prod.
    dev_no_auth: bool = False

    platform_fee_pct: float = 0.05
    accept_window_hours: int = 12
    payment_window_min: int = 15
    dispute_window_hours: int = 48

    payments_provider: str = "stub"  # stub | razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    admin_phone: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost"

    @property
    def is_dev(self) -> bool:
        return self.env != "prod"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
