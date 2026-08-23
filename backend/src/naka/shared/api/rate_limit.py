# backend/src/naka/shared/api/rate_limit.py
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status


def rate_limit(*, limit: int, window_seconds: int) -> Callable[[Request], Awaitable[None]]:
    """Fixed-window rate limiting via Redis INCR/EXPIRE, keyed by route path
    + client IP. Simple on purpose - a taluka-scale public endpoint doesn't
    need a sliding-window algorithm, and this needs no new dependency since
    Redis is already part of the stack (for ARQ)."""

    async def dependency(request: Request) -> None:
        redis = request.app.state.redis
        client_host = request.client.host if request.client else "unknown"
        key = f"ratelimit:{request.url.path}:{client_host}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests, try again shortly"
            )

    return dependency
