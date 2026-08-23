# backend/src/naka/shared/api/deps.py
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.api.security import decode_access_token
from naka.shared.infrastructure.clock import SystemClock
from naka.shared.infrastructure.settings import Settings

_bearer_scheme = HTTPBearer(auto_error=True)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    # Session-per-request, transaction-per-request: the endpoint's use case
    # does its work against this session, and only a clean return commits -
    # any exception (including an HTTPException raised deliberately) rolls
    # back instead of persisting a half-finished change.
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_clock() -> SystemClock:
    return SystemClock()


async def require_ops_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    try:
        payload = decode_access_token(
            credentials.credentials, settings.jwt_secret, settings.jwt_algorithm
        )
    except PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject")
    return subject
