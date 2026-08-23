# backend/tests/enquiry/test_use_cases.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.enquiry.application.dtos import RecordBusinessResponseRequest, SubmitEnquiryRequest
from naka.enquiry.application.errors import EnquiryNotFoundError, InsufficientRoutingCandidatesError
from naka.enquiry.application.ports import RoutingCandidateContact
from naka.enquiry.application.use_cases import (
    ExpireEnquiryWindow,
    GetRoutedRequestByToken,
    ListEnquiryQueue,
    ParseAndRouteEnquiry,
    RecordBusinessResponse,
    SubmitEnquiry,
)
from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.value_objects import EnquiryStatus, ParsedIntent
from naka.shared.domain.ids import BusinessId, EnquiryId
from tests.catalog.factories import make_locality
from tests.enquiry.factories import make_parsed_intent, make_received_enquiry, make_routed_enquiry
from tests.enquiry.fakes import (
    FakeAIClientPort,
    FakeEnquiryRepository,
    FakeLocalityLookupPort,
    FakeMessaging,
    FakeOutbox,
    FakeRoutingCandidateLookupPort,
    FixedClock,
    make_candidate,
)

_NOW = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)


def _token_for(enquiry: Enquiry, business_id: BusinessId) -> str:
    return next(rr.token.value for rr in enquiry.routed_requests if rr.business_id == business_id)


class TestSubmitEnquiry:
    async def test_creates_received_enquiry(self) -> None:
        repo = FakeEnquiryRepository()
        outbox = FakeOutbox()
        use_case = SubmitEnquiry(repo, outbox, FixedClock(_NOW))

        dto = await use_case.execute(
            SubmitEnquiryRequest(
                region_id=make_received_enquiry().region_id.value,
                raw_text="कापसासाठी औषध कोणाकडे आहे?",
                customer_phone="9876543210",
            )
        )

        assert dto.status == EnquiryStatus.RECEIVED.value
        assert len(repo.by_id) == 1
        assert len(outbox.enqueued) == 1


class TestParseAndRouteEnquiry:
    def _use_case(
        self,
        repo: FakeEnquiryRepository,
        *,
        intent: ParsedIntent | None = None,
        candidates: list[RoutingCandidateContact] | None = None,
        messaging: FakeMessaging | None = None,
        outbox: FakeOutbox | None = None,
    ) -> tuple[ParseAndRouteEnquiry, FakeMessaging, FakeOutbox]:
        messaging = messaging or FakeMessaging()
        outbox = outbox or FakeOutbox()
        ai_client = FakeAIClientPort(intent or make_parsed_intent())
        lookup = FakeRoutingCandidateLookupPort(candidates or [])
        use_case = ParseAndRouteEnquiry(
            repo,
            ai_client,
            lookup,
            messaging,
            outbox,
            FixedClock(_NOW),
            response_link_base_url="https://naka.in/r",
        )
        return use_case, messaging, outbox

    async def test_raises_when_enquiry_not_found(self) -> None:
        repo = FakeEnquiryRepository()
        use_case, _, _ = self._use_case(repo)
        with pytest.raises(EnquiryNotFoundError):
            await use_case.execute(EnquiryId.new())

    async def test_advice_request_is_deflected_and_never_routed(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(5)]
        use_case, messaging, _ = self._use_case(
            repo, intent=make_parsed_intent(is_advice_request=True), candidates=candidates
        )

        dto = await use_case.execute(enquiry.id)

        assert dto.status == EnquiryStatus.DEFLECTED.value
        assert messaging.to_business == []

    async def test_routes_and_messages_each_selected_business(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(4)]
        use_case, messaging, outbox = self._use_case(repo, candidates=candidates)

        dto = await use_case.execute(enquiry.id)

        assert dto.status == EnquiryStatus.ROUTED.value
        assert len(dto.routed_business_ids) == 4
        assert len(messaging.to_business) == 4
        for _phone, message in messaging.to_business:
            assert "https://naka.in/r/" in message
        assert any(event.__class__.__name__ == "EnquiryRouted" for event in outbox.enqueued)

    async def test_raises_when_fewer_than_three_candidates(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(2)]
        use_case, _, _ = self._use_case(repo, candidates=candidates)

        with pytest.raises(InsufficientRoutingCandidatesError):
            await use_case.execute(enquiry.id)


class TestRecordBusinessResponse:
    async def test_unknown_token_returns_not_found(self) -> None:
        repo = FakeEnquiryRepository()
        use_case = RecordBusinessResponse(repo, FakeMessaging(), FakeOutbox(), FixedClock(_NOW))

        result = await use_case.execute(
            RecordBusinessResponseRequest(token="does-not-exist", kind="have_it")
        )

        assert result.outcome == "not_found"

    async def test_token_matching_no_routed_request_returns_not_found(self) -> None:
        # Defends against a repo whose get_by_token found *an* enquiry but
        # whose routed_requests don't actually carry that token - shouldn't
        # happen with a correct repo, but this use case doesn't trust that.
        enquiry = make_routed_enquiry()

        class _InconsistentRepo(FakeEnquiryRepository):
            async def get_by_token(self, token: str) -> Enquiry | None:
                return enquiry

        use_case = RecordBusinessResponse(
            _InconsistentRepo(), FakeMessaging(), FakeOutbox(), FixedClock(_NOW)
        )

        result = await use_case.execute(
            RecordBusinessResponseRequest(token="mismatched-token", kind="have_it")
        )

        assert result.outcome == "not_found"

    async def test_first_have_it_is_recorded_and_notifies_customer(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        repo = FakeEnquiryRepository([enquiry])
        messaging = FakeMessaging()
        use_case = RecordBusinessResponse(repo, messaging, FakeOutbox(), FixedClock(_NOW))
        token = _token_for(enquiry, business_a)

        result = await use_case.execute(RecordBusinessResponseRequest(token=token, kind="have_it"))

        assert result.outcome == "recorded"
        assert result.was_first is True
        assert len(messaging.to_customer) == 1

    async def test_second_have_it_is_recorded_without_customer_notification(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        repo = FakeEnquiryRepository([enquiry])
        messaging = FakeMessaging()
        use_case = RecordBusinessResponse(repo, messaging, FakeOutbox(), FixedClock(_NOW))
        token_a = _token_for(enquiry, business_a)
        token_b = _token_for(enquiry, business_b)

        await use_case.execute(RecordBusinessResponseRequest(token=token_a, kind="have_it"))
        result = await use_case.execute(
            RecordBusinessResponseRequest(token=token_b, kind="have_it")
        )

        assert result.outcome == "recorded"
        assert result.was_first is False
        assert len(messaging.to_customer) == 1  # still just the one, from business_a

    async def test_expired_token_returns_expired(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        repo = FakeEnquiryRepository([enquiry])
        use_case = RecordBusinessResponse(
            repo, FakeMessaging(), FakeOutbox(), FixedClock(_NOW + dt.timedelta(hours=2))
        )
        token = _token_for(enquiry, business_a)

        result = await use_case.execute(RecordBusinessResponseRequest(token=token, kind="have_it"))

        assert result.outcome == "expired"

    async def test_duplicate_response_returns_already_responded(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        repo = FakeEnquiryRepository([enquiry])
        use_case = RecordBusinessResponse(repo, FakeMessaging(), FakeOutbox(), FixedClock(_NOW))
        token = _token_for(enquiry, business_a)

        await use_case.execute(RecordBusinessResponseRequest(token=token, kind="dont_have"))
        result = await use_case.execute(RecordBusinessResponseRequest(token=token, kind="have_it"))

        assert result.outcome == "already_responded"


class TestExpireEnquiryWindow:
    async def test_expires_due_enquiries_and_notifies_customer(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        messaging = FakeMessaging()
        use_case = ExpireEnquiryWindow(
            repo, messaging, FakeOutbox(), FixedClock(_NOW + dt.timedelta(hours=1))
        )

        summaries = await use_case.execute()

        assert len(summaries) == 1
        assert summaries[0].enquiry_id == enquiry.id.value
        assert repo.by_id[enquiry.id].status is EnquiryStatus.UNANSWERED
        assert len(messaging.to_customer) == 1

    async def test_does_not_touch_enquiries_not_yet_due(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        messaging = FakeMessaging()
        use_case = ExpireEnquiryWindow(
            repo, messaging, FakeOutbox(), FixedClock(_NOW + dt.timedelta(minutes=1))
        )

        summaries = await use_case.execute()

        assert summaries == []
        assert messaging.to_customer == []


class TestGetRoutedRequestByToken:
    async def test_unknown_token_returns_not_found(self) -> None:
        repo = FakeEnquiryRepository()
        use_case = GetRoutedRequestByToken(repo, FakeLocalityLookupPort(), FixedClock(_NOW))

        dto = await use_case.execute("does-not-exist")

        assert dto.outcome == "not_found"

    async def test_token_matching_no_routed_request_returns_not_found(self) -> None:
        # Same defensive guard as RecordBusinessResponse: a repo whose
        # get_by_token found *an* enquiry but whose routed_requests don't
        # actually carry that token shouldn't happen, but this use case
        # doesn't trust that either.
        enquiry = make_routed_enquiry()

        class _InconsistentRepo(FakeEnquiryRepository):
            async def get_by_token(self, token: str) -> Enquiry | None:
                return enquiry

        use_case = GetRoutedRequestByToken(
            _InconsistentRepo(), FakeLocalityLookupPort(), FixedClock(_NOW)
        )

        dto = await use_case.execute("mismatched-token")

        assert dto.outcome == "not_found"

    async def test_found_token_returns_page_data_with_locality_name(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        token = enquiry.routed_requests[0].token.value
        locality = make_locality(id=enquiry.locality_id, name_mr="पिंपळनेर")
        localities = FakeLocalityLookupPort({locality.id: locality.name_mr})
        use_case = GetRoutedRequestByToken(
            repo, localities, FixedClock(_NOW + dt.timedelta(minutes=5))
        )

        dto = await use_case.execute(token)

        assert dto.outcome == "found"
        assert dto.raw_text == enquiry.raw_text
        assert dto.locality_id == enquiry.locality_id.value
        assert dto.locality_name == "पिंपळनेर"
        assert dto.minutes_ago == 5
        assert dto.is_expired is False
        assert dto.has_responded is False

    async def test_unknown_locality_leaves_locality_name_none(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        token = enquiry.routed_requests[0].token.value
        use_case = GetRoutedRequestByToken(repo, FakeLocalityLookupPort(), FixedClock(_NOW))

        dto = await use_case.execute(token)

        assert dto.outcome == "found"
        assert dto.locality_name is None

    async def test_expired_token_is_flagged_but_still_found(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        token = enquiry.routed_requests[0].token.value
        use_case = GetRoutedRequestByToken(
            repo, FakeLocalityLookupPort(), FixedClock(_NOW + dt.timedelta(hours=2))
        )

        dto = await use_case.execute(token)

        assert dto.outcome == "found"
        assert dto.is_expired is True


class TestListEnquiryQueue:
    async def test_orders_most_recent_first(self) -> None:
        older = make_received_enquiry(created_at=_NOW - dt.timedelta(hours=1))
        newer = make_received_enquiry(created_at=_NOW)
        repo = FakeEnquiryRepository([older, newer])
        use_case = ListEnquiryQueue(repo, FixedClock(_NOW))

        items = await use_case.execute()

        assert [item.id for item in items] == [newer.id.value, older.id.value]

    async def test_reports_minutes_ago_and_status(self) -> None:
        enquiry = make_received_enquiry(created_at=_NOW - dt.timedelta(minutes=15))
        repo = FakeEnquiryRepository([enquiry])
        use_case = ListEnquiryQueue(repo, FixedClock(_NOW))

        [item] = await use_case.execute()

        assert item.minutes_ago == 15
        assert item.status == EnquiryStatus.RECEIVED.value
        assert item.raw_text == enquiry.raw_text
