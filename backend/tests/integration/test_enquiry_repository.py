# backend/tests/integration/test_enquiry_repository.py
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.enquiry.domain.entities import BusinessResponse
from naka.enquiry.domain.value_objects import EnquiryStatus, ResponseKind
from naka.enquiry.infrastructure.repositories import SqlAlchemyEnquiryRepository
from naka.shared.domain.ids import BusinessId, EnquiryId
from tests.enquiry.factories import (
    NOW,
    make_parsed_enquiry,
    make_received_enquiry,
    make_routed_enquiry,
)

pytestmark = pytest.mark.integration


class TestSqlAlchemyEnquiryRepository:
    async def test_get_returns_none_when_missing(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        assert await repo.get(EnquiryId.new()) is None

    async def test_round_trips_a_received_enquiry(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        enquiry = make_received_enquiry()

        await repo.add(enquiry)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(enquiry.id)
        assert loaded == enquiry

    async def test_round_trips_parsed_intent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        enquiry = make_parsed_enquiry()

        await repo.add(enquiry)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(enquiry.id)
        assert loaded is not None
        assert loaded.parsed_intent == enquiry.parsed_intent
        assert loaded.status is EnquiryStatus.PARSED

    async def test_round_trips_routed_requests_and_finds_by_token(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        enquiry = make_routed_enquiry()

        await repo.add(enquiry)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(enquiry.id)
        assert loaded is not None
        assert len(loaded.routed_requests) == 3

        token = enquiry.routed_requests[0].token.value
        by_token = await repo.get_by_token(token)
        assert by_token is not None
        assert by_token.id == enquiry.id

    async def test_get_by_token_returns_none_for_unknown_token(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        assert await repo.get_by_token("no-such-token") is None

    async def test_update_persists_a_recorded_response(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        business_a = BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, BusinessId.new(), BusinessId.new()))
        await repo.add(enquiry)
        await db_session.flush()

        response = BusinessResponse(
            business_id=business_a,
            kind=ResponseKind.HAVE_IT,
            responded_at=NOW + dt.timedelta(minutes=5),
        )
        updated, _ = enquiry.record_response(response, NOW + dt.timedelta(minutes=5))
        await repo.update(updated)
        await db_session.flush()
        db_session.expunge_all()

        loaded = await repo.get(enquiry.id)
        assert loaded is not None
        assert loaded.status is EnquiryStatus.ANSWERED
        assert len(loaded.responses) == 1
        assert loaded.responses[0].business_id == business_a
        routed_a = next(rr for rr in loaded.routed_requests if rr.business_id == business_a)
        assert routed_a.has_responded is True

    async def test_list_routed_only_returns_routed_status(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        routed = make_routed_enquiry()
        received = make_received_enquiry()
        await repo.add(routed)
        await repo.add(received)
        await db_session.flush()
        db_session.expunge_all()

        results = await repo.list_routed()
        result_ids = {e.id for e in results}
        assert routed.id in result_ids
        assert received.id not in result_ids

    async def test_list_recent_orders_newest_first_and_respects_limit(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyEnquiryRepository(db_session)
        older = make_received_enquiry(created_at=NOW - dt.timedelta(hours=1))
        newer = make_received_enquiry(created_at=NOW)
        await repo.add(older)
        await repo.add(newer)
        await db_session.flush()
        db_session.expunge_all()

        [only] = await repo.list_recent(limit=1)
        assert only.id == newer.id
