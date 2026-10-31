"""Process-local TTL key-value store (replaces Redis).

Used for OTP storage, rate-limit counters, order idempotency keys. Suited to a
single-instance deployment — the store lives in process memory, so a restart
clears it (users simply re-request an OTP). If the API is ever scaled past one
replica, swap this back to Redis/Valkey via REDIS_URL.
"""

import time
from functools import lru_cache


class TTLStore:
    """Minimal async KV with the Redis commands the app uses."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}

    def _drop_if_expired(self, key: str) -> None:
        item = self._data.get(key)
        if item is not None and item[1] is not None and item[1] <= time.monotonic():
            del self._data[key]

    async def get(self, key: str) -> str | None:
        self._drop_if_expired(key)
        item = self._data.get(key)
        return item[0] if item else None

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if nx and await self.get(key) is not None:
            return False
        self._data[key] = (value, time.monotonic() + ex if ex else None)
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            self._drop_if_expired(key)
            if self._data.pop(key, None) is not None:
                removed += 1
        return removed

    async def incr(self, key: str) -> int:
        self._drop_if_expired(key)
        value, expiry = self._data.get(key, ("0", None))
        value = str(int(value) + 1)
        self._data[key] = (value, expiry)
        return int(value)

    async def expire(self, key: str, seconds: int) -> bool:
        self._drop_if_expired(key)
        if key not in self._data:
            return False
        self._data[key] = (self._data[key][0], time.monotonic() + seconds)
        return True


@lru_cache
def get_kv() -> TTLStore:
    return TTLStore()
