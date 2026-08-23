# backend/tests/api/fakes.py
from __future__ import annotations

from typing import Any


class FakeRedis:
    """Rate limiting's INCR/EXPIRE against an in-memory counter - real
    behavior (counts actually go up, expiry is a no-op since tests don't
    need real TTLs), no live Redis needed for router-level tests."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None


class StubUseCase:
    """A generic stand-in for any use case's `execute(...)`. Router tests
    exercise the HTTP contract - status codes, request validation, auth
    enforcement, response shape, error mapping - not use case business
    logic, which is already covered by tests/*/test_use_cases.py."""

    def __init__(self, result: Any = None, exception: Exception | None = None) -> None:
        self.result = result
        self.exception = exception
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if self.exception is not None:
            raise self.exception
        return self.result
