# backend/tests/integration/test_locality_lookup.py
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.infrastructure.repositories import SqlAlchemyLocalityRepository
from naka.enquiry.infrastructure.locality_lookup import SqlLocalityNameLookup
from naka.shared.domain.ids import LocalityId
from tests.catalog.factories import make_locality

pytestmark = pytest.mark.integration


class TestSqlLocalityNameLookup:
    async def test_returns_the_marathi_name(self, db_session: AsyncSession) -> None:
        locality = make_locality(name_mr="पिंपळनेर")
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await db_session.flush()
        db_session.expunge_all()

        lookup = SqlLocalityNameLookup(db_session)
        assert await lookup.get_name(locality.id) == "पिंपळनेर"

    async def test_returns_none_for_unknown_locality(self, db_session: AsyncSession) -> None:
        lookup = SqlLocalityNameLookup(db_session)
        assert await lookup.get_name(LocalityId.new()) is None
