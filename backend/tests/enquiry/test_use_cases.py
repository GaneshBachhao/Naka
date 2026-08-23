# backend/tests/enquiry/test_use_cases.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.enquiry.application.dtos import RecordBusinessResponseRequest, SubmitEnquiryRequest
from naka.enquiry.application.errors import (
    EnquiryNotFoundError,
    InsufficientRoutingCandidatesError,
    InvalidRoutingSelectionError,
)
from naka.enquiry.application.ports import RoutingCandidateContact
from naka.enquiry.application.use_cases import (
    ExpireEnquiryWindow,
    GetDailyCounters,
    GetEnquiryDetail,
    GetRoutedRequestByToken,
    ListEnquiryQueue,
    ParseEnquiry,
    RecordBusinessResponse,
    RouteEnquiry,
    SubmitEnquiry,
    SuggestRoutingCandidates,
)
from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.value_objects import EnquiryStatus
from naka.shared.domain.ids import BusinessId, EnquiryId
from tests.catalog.factories import make_locality
from tests.enquiry.factories import (
    make_parsed_enquiry,
    make_parsed_intent,
    make_received_enquiry,
    make_response,
    make_routed_enquiry,
)
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


class TestParseEnquiry:
    async def test_raises_when_enquiry_not_found(self) -> None:
        repo = FakeEnquiryRepository()
        use_case = ParseEnquiry(
            repo, FakeAIClientPort(make_parsed_intent()), FakeOutbox(), FixedClock(_NOW)
        )
        with pytest.raises(EnquiryNotFoundError):
            await use_case.execute(EnquiryId.new())

    async def test_advice_request_is_deflected(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        ai_client = FakeAIClientPort(make_parsed_intent(is_advice_request=True))
        use_case = ParseEnquiry(repo, ai_client, FakeOutbox(), FixedClock(_NOW))

        dto = await use_case.execute(enquiry.id)

        assert dto.status == EnquiryStatus.DEFLECTED.value

    async def test_parses_and_persists_the_intent(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        outbox = FakeOutbox()
        use_case = ParseEnquiry(
            repo, FakeAIClientPort(make_parsed_intent()), outbox, FixedClock(_NOW)
        )

        dto = await use_case.execute(enquiry.id)

        assert dto.status == EnquiryStatus.PARSED.value
        assert repo.by_id[enquiry.id].category_id is not None


class TestSuggestRoutingCandidates:
    async def test_raises_when_enquiry_not_found(self) -> None:
        use_case = SuggestRoutingCandidates(
            FakeEnquiryRepository(), FakeRoutingCandidateLookupPort()
        )
        with pytest.raises(EnquiryNotFoundError):
            await use_case.execute(EnquiryId.new())

    async def test_returns_no_suggestions_before_parsing(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        use_case = SuggestRoutingCandidates(repo, FakeRoutingCandidateLookupPort())

        suggestions = await use_case.execute(enquiry.id)

        assert suggestions == []

    async def test_returns_every_eligible_candidate_ranked_with_default_top_five(self) -> None:
        enquiry = make_parsed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [
            make_candidate(business_id=BusinessId.new(), distance_km=float(i)) for i in range(7)
        ]
        use_case = SuggestRoutingCandidates(repo, FakeRoutingCandidateLookupPort(candidates))

        suggestions = await use_case.execute(enquiry.id)

        assert len(suggestions) == 7
        assert [s.default_selected for s in suggestions] == [True] * 5 + [False] * 2
        assert suggestions[0].distance_km == 0.0
        assert all(s.reason for s in suggestions)


class TestRouteEnquiry:
    def _use_case(
        self,
        repo: FakeEnquiryRepository,
        *,
        candidates: list[RoutingCandidateContact] | None = None,
        messaging: FakeMessaging | None = None,
        outbox: FakeOutbox | None = None,
    ) -> tuple[RouteEnquiry, FakeMessaging, FakeOutbox]:
        messaging = messaging or FakeMessaging()
        outbox = outbox or FakeOutbox()
        lookup = FakeRoutingCandidateLookupPort(candidates or [])
        use_case = RouteEnquiry(
            repo,
            lookup,
            messaging,
            outbox,
            FixedClock(_NOW),
            response_link_base_url="https://naka.in/r",
        )
        return use_case, messaging, outbox

    async def test_raises_when_enquiry_not_found(self) -> None:
        use_case, _, _ = self._use_case(FakeEnquiryRepository())
        with pytest.raises(EnquiryNotFoundError):
            await use_case.execute(EnquiryId.new(), [BusinessId.new() for _ in range(3)])

    async def test_raises_when_enquiry_has_not_been_parsed(self) -> None:
        enquiry = make_received_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        use_case, _, _ = self._use_case(repo)

        with pytest.raises(InsufficientRoutingCandidatesError):
            await use_case.execute(enquiry.id, [BusinessId.new() for _ in range(3)])

    async def test_routes_and_messages_each_selected_business(self) -> None:
        enquiry = make_parsed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(4)]
        chosen = [c.candidate.business_id for c in candidates]
        use_case, messaging, outbox = self._use_case(repo, candidates=candidates)

        result = await use_case.execute(enquiry.id, chosen)

        assert result.enquiry.status == EnquiryStatus.ROUTED.value
        assert len(result.messages) == 4
        assert len(messaging.to_business) == 4
        for message in result.messages:
            assert "https://naka.in/r/" in message.message
        assert any(event.__class__.__name__ == "EnquiryRouted" for event in outbox.enqueued)

    async def test_rejects_a_business_not_among_eligible_candidates(self) -> None:
        enquiry = make_parsed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(3)]
        use_case, _, _ = self._use_case(repo, candidates=candidates)
        chosen = [c.candidate.business_id for c in candidates[:2]] + [BusinessId.new()]

        with pytest.raises(InvalidRoutingSelectionError):
            await use_case.execute(enquiry.id, chosen)

    async def test_rejects_fewer_than_three_selected(self) -> None:
        enquiry = make_parsed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        candidates = [make_candidate(business_id=BusinessId.new()) for _ in range(3)]
        use_case, _, _ = self._use_case(repo, candidates=candidates)
        chosen = [c.candidate.business_id for c in candidates[:2]]

        with pytest.raises(ValueError, match="fan-out"):
            await use_case.execute(enquiry.id, chosen)


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


class TestGetEnquiryDetail:
    async def test_raises_when_enquiry_not_found(self) -> None:
        use_case = GetEnquiryDetail(FakeEnquiryRepository(), FixedClock(_NOW))
        with pytest.raises(EnquiryNotFoundError):
            await use_case.execute(EnquiryId.new())

    async def test_returns_parsed_intent_and_routed_requests(self) -> None:
        enquiry = make_routed_enquiry()
        repo = FakeEnquiryRepository([enquiry])
        use_case = GetEnquiryDetail(repo, FixedClock(_NOW + dt.timedelta(minutes=5)))

        detail = await use_case.execute(enquiry.id)

        assert detail.status == EnquiryStatus.ROUTED.value
        assert detail.minutes_ago == 5
        assert detail.parsed_intent is not None
        assert enquiry.category_id is not None
        assert detail.parsed_intent.category_id == enquiry.category_id.value
        assert len(detail.routed_requests) == 3
        assert detail.winning_business_id is None

    async def test_reports_the_winning_business_and_its_response(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        responded_at = _NOW + dt.timedelta(minutes=2)
        response = make_response(business_id=business_a, responded_at=responded_at)
        answered, _ = enquiry.record_response(response, responded_at)
        repo = FakeEnquiryRepository([answered])
        use_case = GetEnquiryDetail(repo, FixedClock(_NOW + dt.timedelta(minutes=5)))

        detail = await use_case.execute(answered.id)

        assert detail.winning_business_id == business_a.value
        assert len(detail.responses) == 1
        assert detail.responses[0].business_id == business_a.value


class TestGetDailyCounters:
    async def test_counts_only_todays_enquiries(self) -> None:
        today = make_received_enquiry(created_at=_NOW)
        yesterday = make_received_enquiry(created_at=_NOW - dt.timedelta(days=1))
        repo = FakeEnquiryRepository([today, yesterday])
        use_case = GetDailyCounters(repo, FixedClock(_NOW))

        counters = await use_case.execute()

        assert counters.total_enquiries == 1

    async def test_computes_answer_rate_and_median_response_time(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        start_of_day = _NOW.replace(hour=0, minute=0, second=0, microsecond=0)

        enquiry_1 = make_routed_enquiry(
            business_ids=(business_a, business_b, business_c),
            created_at=start_of_day + dt.timedelta(hours=1),
        )
        responded_at = enquiry_1.created_at + dt.timedelta(minutes=5)
        response = make_response(business_id=business_a, responded_at=responded_at)
        answered_1, _ = enquiry_1.record_response(response, responded_at)

        unanswered_2 = make_routed_enquiry(
            business_ids=(business_a, business_b, business_c),
            created_at=start_of_day + dt.timedelta(hours=2),
        )

        repo = FakeEnquiryRepository([answered_1, unanswered_2])
        use_case = GetDailyCounters(repo, FixedClock(_NOW))

        counters = await use_case.execute()

        assert counters.total_enquiries == 2
        assert counters.answered == 1
        assert counters.answer_rate == 0.5
        assert counters.median_response_seconds == 300

    async def test_returns_none_median_when_nothing_answered(self) -> None:
        enquiry = make_received_enquiry(created_at=_NOW)
        repo = FakeEnquiryRepository([enquiry])
        use_case = GetDailyCounters(repo, FixedClock(_NOW))

        counters = await use_case.execute()

        assert counters.answer_rate == 0.0
        assert counters.median_response_seconds is None
