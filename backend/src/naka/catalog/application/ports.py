# backend/src/naka/catalog/application/ports.py
from __future__ import annotations

from typing import Protocol

from naka.catalog.domain.entities import Business, Category, Locality, Region
from naka.shared.domain.ids import BusinessId, RegionId


class BusinessRepository(Protocol):
    async def get(self, business_id: BusinessId) -> Business | None: ...

    async def add(self, business: Business) -> None: ...

    async def update(self, business: Business) -> None: ...

    async def list_all(self) -> list[Business]: ...


class RegionRepository(Protocol):
    async def get_by_slug(self, slug: str) -> Region | None: ...


class LocalityRepository(Protocol):
    async def list_by_region(self, region_id: RegionId) -> list[Locality]: ...


class CategoryRepository(Protocol):
    async def list_all(self) -> list[Category]: ...
