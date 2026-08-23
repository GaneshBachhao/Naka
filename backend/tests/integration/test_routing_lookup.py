# backend/tests/integration/test_routing_lookup.py
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.domain.entities import PublicationState
from naka.catalog.domain.value_objects import Coordinates
from naka.catalog.infrastructure.repositories import (
    SqlAlchemyBusinessRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyLocalityRepository,
)
from naka.enquiry.domain.entities import BusinessResponse
from naka.enquiry.domain.value_objects import ResponseKind
from naka.enquiry.infrastructure.repositories import SqlAlchemyEnquiryRepository
from naka.enquiry.infrastructure.routing_lookup import SqlRoutingCandidateLookupPort
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId
from naka.verification.domain.entities import VerificationTier
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository
from tests.catalog.factories import make_business, make_category, make_locality
from tests.enquiry.factories import NOW, make_routed_enquiry
from tests.verification.factories import make_record

pytestmark = pytest.mark.integration


class _FixedClock:
    def now(self) -> dt.datetime:
        return NOW


class TestSqlRoutingCandidateLookupPort:
    async def test_returns_empty_for_unknown_locality(self, db_session: AsyncSession) -> None:
        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        results = await port.find_candidates(CategoryId.new(), LocalityId.new())
        assert results == []

    async def test_finds_eligible_business_in_category_and_region(
        self, db_session: AsyncSession
    ) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        locality = make_locality(centroid=Coordinates(latitude=21.0, longitude=74.0))
        business = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            coordinates=Coordinates(latitude=21.01, longitude=74.01),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )

        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await SqlAlchemyBusinessRepository(db_session).add(business)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        results = await port.find_candidates(category.id, locality.id)

        assert len(results) == 1
        assert results[0].candidate.business_id == business.id
        assert results[0].candidate.distance_km < 5.0
        assert results[0].whatsapp_number == business.whatsapp_number

    async def test_excludes_unverified_and_draft_businesses(self, db_session: AsyncSession) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        locality = make_locality()
        unverified = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            publication_state=PublicationState.PUBLISHED_UNVERIFIED,
        )
        draft = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            publication_state=PublicationState.DRAFT,
        )

        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await SqlAlchemyBusinessRepository(db_session).add(unverified)
        await SqlAlchemyBusinessRepository(db_session).add(draft)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        results = await port.find_candidates(category.id, locality.id)

        assert results == []

    async def test_excludes_non_routable_category(self, db_session: AsyncSession) -> None:
        category = make_category(slug="government-office", routable=False)
        locality = make_locality()
        business = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )

        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await SqlAlchemyBusinessRepository(db_session).add(business)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        results = await port.find_candidates(category.id, locality.id)

        assert results == []

    async def test_computes_response_rate_and_recency_from_history(
        self, db_session: AsyncSession
    ) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        locality = make_locality()
        business = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )
        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await SqlAlchemyBusinessRepository(db_session).add(business)

        # one past enquiry this business answered, alongside two other businesses
        past_enquiry = make_routed_enquiry(
            business_ids=(business.id, BusinessId.new(), BusinessId.new())
        )
        response = BusinessResponse(
            business_id=business.id,
            kind=ResponseKind.HAVE_IT,
            responded_at=NOW + dt.timedelta(minutes=1),
        )
        answered, _ = past_enquiry.record_response(response, NOW + dt.timedelta(minutes=1))
        await SqlAlchemyEnquiryRepository(db_session).add(answered)

        record = make_record(
            business_id=business.id,
            tier=VerificationTier.FIELD_VERIFIED,
            verified_at=NOW - dt.timedelta(days=10),
        )
        await SqlAlchemyVerificationRecordRepository(db_session).add(record)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        [result] = await port.find_candidates(category.id, locality.id)

        assert result.candidate.response_rate == 1.0
        assert result.candidate.verification_recency_days == 10

    async def test_never_verified_business_gets_worst_recency(
        self, db_session: AsyncSession
    ) -> None:
        category = make_category(slug="agri-input-dealer", routable=True)
        locality = make_locality()
        business = make_business(
            region_id=locality.region_id,
            locality_id=locality.id,
            category_ids=(category.id,),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )
        await SqlAlchemyCategoryRepository(db_session).add(category)
        await SqlAlchemyLocalityRepository(db_session).add(locality)
        await SqlAlchemyBusinessRepository(db_session).add(business)
        await db_session.flush()
        db_session.expunge_all()

        port = SqlRoutingCandidateLookupPort(db_session, _FixedClock())
        [result] = await port.find_candidates(category.id, locality.id)

        assert result.candidate.verification_recency_days == 10_000
        assert result.candidate.response_rate == 0.0
