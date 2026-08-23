# backend/tests/catalog/fakes.py
from __future__ import annotations

from naka.catalog.domain.entities import Business, Category, Locality
from naka.shared.domain.ids import BusinessId, RegionId


class FakeBusinessRepository:
    def __init__(self) -> None:
        self.businesses: dict[BusinessId, Business] = {}

    async def get(self, business_id: BusinessId) -> Business | None:
        return self.businesses.get(business_id)

    async def add(self, business: Business) -> None:
        self.businesses[business.id] = business

    async def update(self, business: Business) -> None:
        self.businesses[business.id] = business

    async def list_all(self) -> list[Business]:
        return list(self.businesses.values())


class FakeLocalityRepository:
    def __init__(self, localities: list[Locality] | None = None) -> None:
        self.localities = localities or []

    async def list_by_region(self, region_id: RegionId) -> list[Locality]:
        return [loc for loc in self.localities if loc.region_id == region_id]


class FakeCategoryRepository:
    def __init__(self, categories: list[Category] | None = None) -> None:
        self.categories = categories or []

    async def list_all(self) -> list[Category]:
        return list(self.categories)
