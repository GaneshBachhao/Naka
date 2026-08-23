# backend/src/naka/catalog/infrastructure/repositories.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.domain.entities import Business, Category, Locality, Region
from naka.catalog.infrastructure.mappers import (
    business_to_domain,
    business_to_model,
    category_to_domain,
    category_to_model,
    locality_to_domain,
    locality_to_model,
    region_to_domain,
    region_to_model,
)
from naka.catalog.infrastructure.models import (
    BusinessModel,
    CategoryModel,
    LocalityModel,
    RegionModel,
)
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId


class SqlAlchemyBusinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, business_id: BusinessId) -> Business | None:
        model = await self._session.get(BusinessModel, business_id.value)
        return business_to_domain(model) if model is not None else None

    async def add(self, business: Business) -> None:
        self._session.add(business_to_model(business))

    async def update(self, business: Business) -> None:
        await self._session.merge(business_to_model(business))

    async def list_all(self) -> list[Business]:
        result = await self._session.execute(select(BusinessModel))
        return [business_to_domain(model) for model in result.scalars().all()]


# Region still has no application-layer port or use case consumer - T10
# (seeding Sakri's region record) will need it. Locality/Category are now
# backed by ListLocalities/ListCategories (T8: the ops console's business
# form needs somewhere to source its dropdowns from).


class SqlAlchemyRegionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, region_id: RegionId) -> Region | None:
        model = await self._session.get(RegionModel, region_id.value)
        return region_to_domain(model) if model is not None else None

    async def add(self, region: Region) -> None:
        self._session.add(region_to_model(region))


class SqlAlchemyLocalityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, locality_id: LocalityId) -> Locality | None:
        model = await self._session.get(LocalityModel, locality_id.value)
        return locality_to_domain(model) if model is not None else None

    async def add(self, locality: Locality) -> None:
        self._session.add(locality_to_model(locality))

    async def list_by_region(self, region_id: RegionId) -> list[Locality]:
        stmt = select(LocalityModel).where(LocalityModel.region_id == region_id.value)
        result = await self._session.execute(stmt)
        return [locality_to_domain(model) for model in result.scalars().all()]


class SqlAlchemyCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, category_id: CategoryId) -> Category | None:
        model = await self._session.get(CategoryModel, category_id.value)
        return category_to_domain(model) if model is not None else None

    async def add(self, category: Category) -> None:
        self._session.add(category_to_model(category))

    async def list_all(self) -> list[Category]:
        result = await self._session.execute(select(CategoryModel))
        return [category_to_domain(model) for model in result.scalars().all()]
