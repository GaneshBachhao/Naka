# backend/src/naka/shared/api/security.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


def create_access_token(
    subject: str,
    secret: str,
    algorithm: str,
    expires_in: timedelta = timedelta(hours=12),
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + expires_in, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=[algorithm])
