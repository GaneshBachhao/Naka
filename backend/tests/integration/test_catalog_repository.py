# backend/tests/integration/test_catalog_repository.py
from __future__ import annotations

from datetime import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.domain.entities import PublicationState
from naka.catalog.domain.value_objects import DayHours, OpeningHours, Weekday
from naka.catalog.infrastructure.repositories import (
    SqlAlchemyBusinessRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyLocalityRepository,
    SqlAlchemyRegionRepository,
)
from naka.shared.domain.ids import BusinessId, RegionId
from tests.catalog.factories import make_business, make_category, make_locality, make_region

pytestmark = pytest.mark.integration


class TestSqlAlchemyBusinessRepository:
    async def test_get_returns_none_when_missing(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyBusinessRepository(db_session)
        assert await repo.get(BusinessId.new()) is None

    async def test_round_trips_a_business(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyBusinessRepository(db_session)
        business = make_business()

        await repo.add(business)
        await db_session.flush()

        loaded = await repo.get(business.id)
        assert loaded == business

    async def test_update_persists_state_transition(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyBusinessRepository(db_session)
        business = make_business(publication_state=PublicationState.DRAFT)
        await repo.add(business)
        await db_session.flush()

        published = business.publish()
        await repo.update(published)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(business.id)
        assert loaded is not None
        assert loaded.publication_state is PublicationState.PUBLISHED_UNVERIFIED

    async def test_round_trip_preserves_opening_hours_with_midday_break(
        self, db_session: AsyncSession
    ) -> None:
        by_day = {
            day: DayHours(
                open_time=time(9, 0),
                close_time=time(21, 0),
                midday_break_start=time(13, 0),
                midday_break_end=time(14, 0),
            )
            for day in Weekday
        }
        business = make_business(opening_hours=OpeningHours(by_day=by_day))
        repo = SqlAlchemyBusinessRepository(db_session)
        await repo.add(business)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(business.id)
        assert loaded is not None
        assert loaded.opening_hours == business.opening_hours

    async def test_list_all_returns_every_business(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyBusinessRepository(db_session)
        first = make_business()
        second = make_business()

        await repo.add(first)
        await repo.add(second)
        await db_session.flush()
        db_session.expunge_all()

        results = await repo.list_all()
        assert {b.id for b in results} == {first.id, second.id}


class TestSqlAlchemyRegionRepository:
    async def test_get_returns_none_when_missing(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRegionRepository(db_session)
        assert await repo.get(RegionId.new()) is None

    async def test_round_trips_a_region(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyRegionRepository(db_session)
        region = make_region()

        await repo.add(region)
        await db_session.flush()
        db_session.expunge_all()

        assert await repo.get(region.id) == region


class TestSqlAlchemyLocalityRepository:
    async def test_round_trips_a_locality(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLocalityRepository(db_session)
        locality = make_locality()

        await repo.add(locality)
        await db_session.flush()
        db_session.expunge_all()

        assert await repo.get(locality.id) == locality

    async def test_round_trips_a_locality_with_no_market_day(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyLocalityRepository(db_session)
        locality = make_locality(market_day=None)

        await repo.add(locality)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(locality.id)
        assert loaded is not None
        assert loaded.market_day is None

    async def test_list_by_region_filters_correctly(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLocalityRepository(db_session)
        region_a = RegionId.new()
        region_b = RegionId.new()
        in_region = make_locality(region_id=region_a)
        other_region = make_locality(region_id=region_b)

        await repo.add(in_region)
        await repo.add(other_region)
        await db_session.flush()
        db_session.expunge_all()

        results = await repo.list_by_region(region_a)
        assert [loc.id for loc in results] == [in_region.id]


class TestSqlAlchemyCategoryRepository:
    async def test_round_trips_a_category(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCategoryRepository(db_session)
        category = make_category()

        await repo.add(category)
        await db_session.flush()
        db_session.expunge_all()

        assert await repo.get(category.id) == category

    async def test_round_trips_a_category_with_a_parent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCategoryRepository(db_session)
        parent = make_category(slug="agriculture")
        child = make_category(slug="pesticide-dealer", parent_id=parent.id)

        await repo.add(parent)
        await repo.add(child)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(child.id)
        assert loaded is not None
        assert loaded.parent_id == parent.id

    async def test_list_all_returns_every_category(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCategoryRepository(db_session)
        first = make_category(slug="agri-input-dealer")
        second = make_category(slug="pharmacy")

        await repo.add(first)
        await repo.add(second)
        await db_session.flush()
        db_session.expunge_all()

        results = await repo.list_all()
        assert {c.id for c in results} == {first.id, second.id}
