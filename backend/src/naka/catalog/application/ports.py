# backend/src/naka/catalog/application/ports.py
from __future__ import annotations

from typing import Protocol

from naka.catalog.domain.entities import Business
from naka.shared.domain.ids import BusinessId


class BusinessRepository(Protocol):
    async def get(self, business_id: BusinessId) -> Business | None: ...

    async def add(self, business: Business) -> None: ...

    async def update(self, business: Business) -> None: ...
