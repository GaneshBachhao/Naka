# backend/tests/integration/test_reverification_signals.py
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.infrastructure.repositories import (
    SqlAlchemyBusinessRepository,
    SqlAlchemyCategoryRepository,
)
from naka.shared.domain.ids import BusinessId
from naka.verification.infrastructure.reverification_signals import SqlReverificationSignalsPort
from tests.catalog.factories import make_business, make_category

pytestmark = pytest.mark.integration


class TestSqlReverificationSignalsPort:
    async def test_empty_input_returns_empty_dict(self, db_session: AsyncSession) -> None:
        port = SqlReverificationSignalsPort(db_session)
        assert await port.get_signals([]) == {}

    async def test_unknown_business_defaults_to_not_paying_not_routable(
        self, db_session: AsyncSession
    ) -> None:
        port = SqlReverificationSignalsPort(db_session)
        signals = await port.get_signals([BusinessId.new()])
        [value] = signals.values()
        assert value.is_paying is False
        assert value.is_routable_category is False

    async def test_routable_category_is_detected(self, db_session: AsyncSession) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        business = make_business(category_ids=(category.id,))
        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyBusinessRepository(db_session).add(business)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlReverificationSignalsPort(db_session)
        signals = await port.get_signals([business.id])

        assert signals[business.id].is_routable_category is True
        assert signals[business.id].is_paying is False

    async def test_non_routable_category_is_detected(self, db_session: AsyncSession) -> None:
        category = make_category(slug="government-office", routable=False)
        business = make_business(category_ids=(category.id,))
        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyBusinessRepository(db_session).add(business)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlReverificationSignalsPort(db_session)
        signals = await port.get_signals([business.id])

        assert signals[business.id].is_routable_category is False

    async def test_returns_a_signal_for_every_requested_business(
        self, db_session: AsyncSession
    ) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        known = make_business(category_ids=(category.id,))
        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyBusinessRepository(db_session).add(known)
        await db_session.flush()
        db_session.expunge_all()

        unknown = BusinessId.new()
        port = SqlReverificationSignalsPort(db_session)
        signals = await port.get_signals([known.id, unknown])

        assert set(signals) == {known.id, unknown}
        assert signals[known.id].is_routable_category is True
        assert signals[unknown].is_routable_category is False
