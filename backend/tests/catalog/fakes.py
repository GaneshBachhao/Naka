# backend/tests/catalog/fakes.py
from __future__ import annotations

from naka.catalog.domain.entities import Business
from naka.shared.domain.ids import BusinessId


class FakeBusinessRepository:
    def __init__(self) -> None:
        self.businesses: dict[BusinessId, Business] = {}

    async def get(self, business_id: BusinessId) -> Business | None:
        return self.businesses.get(business_id)

    async def add(self, business: Business) -> None:
        self.businesses[business.id] = business

    async def update(self, business: Business) -> None:
        self.businesses[business.id] = business
