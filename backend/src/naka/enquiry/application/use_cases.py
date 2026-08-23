# backend/src/naka/enquiry/application/use_cases.py
from __future__ import annotations

import statistics
from collections.abc import Sequence

from naka.enquiry.application.dtos import (
    BusinessResponseDetailDTO,
    DailyCountersDTO,
    EnquiryDetailDTO,
    EnquiryDTO,
    EnquiryQueueItemDTO,
    ExpiredEnquirySummary,
    ParsedIntentDTO,
    RecordBusinessResponseRequest,
    RecordBusinessResponseResult,
    RoutedMessageDTO,
    RoutedRequestDetailDTO,
    RoutedRequestPageDTO,
    RouteEnquiryResult,
    RoutingSuggestionDTO,
    SubmitEnquiryRequest,
)
from naka.enquiry.application.errors import (
    EnquiryNotFoundError,
    InsufficientRoutingCandidatesError,
    InvalidRoutingSelectionError,
)
from naka.enquiry.application.ports import (
    AIClientPort,
    EnquiryRepository,
    LocalityLookupPort,
    RoutingCandidateLookupPort,
)
from naka.enquiry.domain.entities import BusinessResponse, Enquiry
from naka.enquiry.domain.events import EnquiryAnswered
from naka.enquiry.domain.services import RoutingCandidate, rank_routing_candidates
from naka.enquiry.domain.value_objects import EnquiryStatus, ResponseKind
from naka.shared.application.ports import Clock, MessagingPort, OutboxPort
from naka.shared.domain.ids import BusinessId, EnquiryId, RegionId
from naka.shared.domain.phone_number import PhoneNumber

_DEFAULT_FANOUT = 5


def _routing_reason(candidate: RoutingCandidate) -> str:
    distance = f"{candidate.distance_km:.1f} km away"
    response = f"{candidate.response_rate:.0%} response rate"
    verification = (
        "not verified recently"
        if candidate.verification_recency_days >= 365
        else f"verified {candidate.verification_recency_days}d ago"
    )
    return f"{distance}, {response}, {verification}"


def _to_dto(enquiry: Enquiry) -> EnquiryDTO:
    return EnquiryDTO(
        id=enquiry.id.value,
        status=enquiry.status.value,
        category_id=enquiry.category_id.value if enquiry.category_id else None,
        locality_id=enquiry.locality_id.value if enquiry.locality_id else None,
        routed_business_ids=[rr.business_id.value for rr in enquiry.routed_requests],
    )


class SubmitEnquiry:
    def __init__(self, enquiries: EnquiryRepository, outbox: OutboxPort, clock: Clock) -> None:
        self._enquiries = enquiries
        self._outbox = outbox
        self._clock = clock

    async def execute(self, request: SubmitEnquiryRequest) -> EnquiryDTO:
        enquiry, events = Enquiry.receive(
            id=EnquiryId.new(),
            region_id=RegionId(request.region_id),
            raw_text=request.raw_text,
            customer_phone=PhoneNumber(request.customer_phone),
            created_at=self._clock.now(),
        )
        await self._enquiries.add(enquiry)
        await self._outbox.enqueue(events)
        return _to_dto(enquiry)


class ParseEnquiry:
    """Just intent parsing - split out from routing (T8) so an operator can
    review the parsed category/locality and the ranked suggestions before
    committing to a fan-out, rather than the two happening atomically."""

    def __init__(
        self,
        enquiries: EnquiryRepository,
        ai_client: AIClientPort,
        outbox: OutboxPort,
        clock: Clock,
    ) -> None:
        self._enquiries = enquiries
        self._ai_client = ai_client
        self._outbox = outbox
        self._clock = clock

    async def execute(self, enquiry_id: EnquiryId) -> EnquiryDTO:
        enquiry = await self._enquiries.get(enquiry_id)
        if enquiry is None:
            raise EnquiryNotFoundError(enquiry_id)

        intent = await self._ai_client.parse_enquiry_intent(enquiry.raw_text, enquiry.region_id)
        now = self._clock.now()
        parsed, events = enquiry.apply_parsed_intent(intent, now)
        await self._enquiries.update(parsed)
        await self._outbox.enqueue(events)
        return _to_dto(parsed)


class SuggestRoutingCandidates:
    """Backs the ops console's ranked-with-reasons suggestion list for a
    parsed enquiry. Returns every eligible candidate, not just the top
    fan-out, so an operator can swap a default pick for an alternate before
    routing (KICKOFF T8: "editable")."""

    def __init__(
        self, enquiries: EnquiryRepository, candidates: RoutingCandidateLookupPort
    ) -> None:
        self._enquiries = enquiries
        self._candidates = candidates

    async def execute(self, enquiry_id: EnquiryId) -> list[RoutingSuggestionDTO]:
        enquiry = await self._enquiries.get(enquiry_id)
        if enquiry is None:
            raise EnquiryNotFoundError(enquiry_id)
        if enquiry.category_id is None or enquiry.locality_id is None:
            return []

        found = await self._candidates.find_candidates(enquiry.category_id, enquiry.locality_id)
        ranked = rank_routing_candidates(c.candidate for c in found)
        return [
            RoutingSuggestionDTO(
                business_id=c.business_id.value,
                distance_km=c.distance_km,
                response_rate=c.response_rate,
                verification_recency_days=c.verification_recency_days,
                reason=_routing_reason(c),
                default_selected=i < _DEFAULT_FANOUT,
            )
            for i, c in enumerate(ranked)
        ]


class RouteEnquiry:
    """Routes to the operator's chosen businesses - not necessarily the
    default top-5 SuggestRoutingCandidates proposed, since the operator may
    have edited the selection. Returns the exact WhatsApp message composed
    for each, for the operator to copy and send by hand (Wizard-of-Oz)."""

    def __init__(
        self,
        enquiries: EnquiryRepository,
        candidates: RoutingCandidateLookupPort,
        messaging: MessagingPort,
        outbox: OutboxPort,
        clock: Clock,
        response_link_base_url: str,
    ) -> None:
        self._enquiries = enquiries
        self._candidates = candidates
        self._messaging = messaging
        self._outbox = outbox
        self._clock = clock
        self._response_link_base_url = response_link_base_url

    async def execute(
        self, enquiry_id: EnquiryId, business_ids: Sequence[BusinessId]
    ) -> RouteEnquiryResult:
        enquiry = await self._enquiries.get(enquiry_id)
        if enquiry is None:
            raise EnquiryNotFoundError(enquiry_id)
        if enquiry.category_id is None or enquiry.locality_id is None:
            raise InsufficientRoutingCandidatesError(enquiry_id)

        found = await self._candidates.find_candidates(enquiry.category_id, enquiry.locality_id)
        contact_by_business = {c.candidate.business_id: c.whatsapp_number for c in found}
        if not set(business_ids) <= contact_by_business.keys():
            raise InvalidRoutingSelectionError(enquiry_id)

        now = self._clock.now()
        routed, events = enquiry.route(business_ids, now)
        await self._enquiries.update(routed)
        await self._outbox.enqueue(events)

        messages: list[RoutedMessageDTO] = []
        for routed_request in routed.routed_requests:
            phone_number = contact_by_business[routed_request.business_id]
            link = f"{self._response_link_base_url}/{routed_request.token.value}"
            message = f"{routed.raw_text}\n{link}"
            await self._messaging.send_to_business(phone_number, message)
            messages.append(
                RoutedMessageDTO(
                    business_id=routed_request.business_id.value,
                    phone_number=str(phone_number),
                    message=message,
                )
            )

        return RouteEnquiryResult(enquiry=_to_dto(routed), messages=messages)


class RecordBusinessResponse:
    def __init__(
        self,
        enquiries: EnquiryRepository,
        messaging: MessagingPort,
        outbox: OutboxPort,
        clock: Clock,
    ) -> None:
        self._enquiries = enquiries
        self._messaging = messaging
        self._outbox = outbox
        self._clock = clock

    async def execute(self, request: RecordBusinessResponseRequest) -> RecordBusinessResponseResult:
        enquiry = await self._enquiries.get_by_token(request.token)
        if enquiry is None:
            return RecordBusinessResponseResult(outcome="not_found")

        matching = next(
            (rr for rr in enquiry.routed_requests if rr.token.value == request.token), None
        )
        if matching is None:
            return RecordBusinessResponseResult(outcome="not_found")

        now = self._clock.now()
        if matching.has_responded:
            return RecordBusinessResponseResult(outcome="already_responded")
        if matching.is_expired_at(now):
            return RecordBusinessResponseResult(outcome="expired")

        response = BusinessResponse(
            business_id=matching.business_id,
            kind=ResponseKind(request.kind),
            responded_at=now,
            price_paise=request.price_paise,
            note=request.note,
            can_arrange_by=request.can_arrange_by,
        )
        updated, events = enquiry.record_response(response, now)
        await self._enquiries.update(updated)
        await self._outbox.enqueue(events)

        was_first = any(isinstance(event, EnquiryAnswered) for event in events)
        if was_first:
            await self._messaging.send_to_customer(
                updated.customer_phone, "Good news - someone has what you asked about."
            )
        return RecordBusinessResponseResult(outcome="recorded", was_first=was_first)


class ExpireEnquiryWindow:
    def __init__(
        self,
        enquiries: EnquiryRepository,
        messaging: MessagingPort,
        outbox: OutboxPort,
        clock: Clock,
    ) -> None:
        self._enquiries = enquiries
        self._messaging = messaging
        self._outbox = outbox
        self._clock = clock

    async def execute(self) -> list[ExpiredEnquirySummary]:
        now = self._clock.now()
        expired: list[ExpiredEnquirySummary] = []
        for enquiry in await self._enquiries.list_routed():
            updated, events = enquiry.expire(now)
            if not events:
                continue
            await self._enquiries.update(updated)
            await self._outbox.enqueue(events)
            await self._messaging.send_to_customer(
                updated.customer_phone, "Sorry - nobody answered your enquiry in time."
            )
            expired.append(ExpiredEnquirySummary(enquiry_id=updated.id.value))
        return expired


class GetRoutedRequestByToken:
    """Backs GET /r/{token} - the dealer response page's data source. Not
    found and expired-but-real-token are both normal outcomes here (T7's
    design note: an expired or used token gets its own clear state, not an
    error page), so this returns a DTO rather than raising."""

    def __init__(
        self, enquiries: EnquiryRepository, localities: LocalityLookupPort, clock: Clock
    ) -> None:
        self._enquiries = enquiries
        self._localities = localities
        self._clock = clock

    async def execute(self, token: str) -> RoutedRequestPageDTO:
        enquiry = await self._enquiries.get_by_token(token)
        if enquiry is None:
            return RoutedRequestPageDTO(outcome="not_found")

        matching = next(
            (routed for routed in enquiry.routed_requests if routed.token.value == token), None
        )
        if matching is None:
            return RoutedRequestPageDTO(outcome="not_found")

        locality_name = None
        if enquiry.locality_id is not None:
            locality_name = await self._localities.get_name(enquiry.locality_id)

        now = self._clock.now()
        minutes_ago = int((now - enquiry.created_at).total_seconds() // 60)
        return RoutedRequestPageDTO(
            outcome="found",
            raw_text=enquiry.raw_text,
            locality_id=enquiry.locality_id.value if enquiry.locality_id else None,
            locality_name=locality_name,
            minutes_ago=minutes_ago,
            is_expired=matching.is_expired_at(now),
            has_responded=matching.has_responded,
        )


class ListEnquiryQueue:
    def __init__(self, enquiries: EnquiryRepository, clock: Clock) -> None:
        self._enquiries = enquiries
        self._clock = clock

    async def execute(self, limit: int = 100) -> list[EnquiryQueueItemDTO]:
        now = self._clock.now()
        return [
            EnquiryQueueItemDTO(
                id=enquiry.id.value,
                status=enquiry.status.value,
                raw_text=enquiry.raw_text,
                minutes_ago=int((now - enquiry.created_at).total_seconds() // 60),
            )
            for enquiry in await self._enquiries.list_recent(limit)
        ]


class GetEnquiryDetail:
    """Backs the ops console's one-enquiry view: parsed intent, every routed
    request, and every response recorded so far - polled by the frontend so
    answers show up as they arrive (KICKOFF T8: "response tracking")."""

    def __init__(self, enquiries: EnquiryRepository, clock: Clock) -> None:
        self._enquiries = enquiries
        self._clock = clock

    async def execute(self, enquiry_id: EnquiryId) -> EnquiryDetailDTO:
        enquiry = await self._enquiries.get(enquiry_id)
        if enquiry is None:
            raise EnquiryNotFoundError(enquiry_id)

        now = self._clock.now()
        intent = enquiry.parsed_intent
        parsed_intent_dto = (
            ParsedIntentDTO(
                category_id=intent.category_id.value,
                item_text=intent.item_text,
                locality_id=intent.locality_id.value,
                urgency=intent.urgency.value,
                confidence=intent.confidence,
                is_advice_request=intent.is_advice_request,
            )
            if intent is not None
            else None
        )
        winning = enquiry.winning_response
        return EnquiryDetailDTO(
            id=enquiry.id.value,
            status=enquiry.status.value,
            raw_text=enquiry.raw_text,
            region_id=enquiry.region_id.value,
            created_at=enquiry.created_at,
            minutes_ago=int((now - enquiry.created_at).total_seconds() // 60),
            parsed_intent=parsed_intent_dto,
            routed_requests=[
                RoutedRequestDetailDTO(
                    business_id=rr.business_id.value,
                    sent_at=rr.sent_at,
                    expires_at=rr.expires_at,
                    responded_at=rr.responded_at,
                    is_expired=rr.is_expired_at(now),
                )
                for rr in enquiry.routed_requests
            ],
            responses=[
                BusinessResponseDetailDTO(
                    business_id=r.business_id.value,
                    kind=r.kind.value,
                    price_paise=r.price_paise,
                    note=r.note,
                    can_arrange_by=r.can_arrange_by,
                    responded_at=r.responded_at,
                )
                for r in enquiry.responses
            ],
            winning_business_id=winning.business_id.value if winning is not None else None,
        )


class GetDailyCounters:
    """Today's enquiries, answer rate, and median time-to-answer, for the
    ops console's always-visible counter strip. "Today" is a UTC calendar
    day, per CLAUDE.md's "all timestamps UTC, display converts to IST" -
    the frontend is where an IST-local "today" would belong, not here."""

    def __init__(self, enquiries: EnquiryRepository, clock: Clock) -> None:
        self._enquiries = enquiries
        self._clock = clock

    async def execute(self) -> DailyCountersDTO:
        now = self._clock.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        todays = await self._enquiries.list_since(start_of_day)

        total = len(todays)
        answered = [e for e in todays if e.status is EnquiryStatus.ANSWERED]
        response_seconds = [
            (e.winning_response.responded_at - e.created_at).total_seconds()
            for e in answered
            if e.winning_response is not None
        ]
        return DailyCountersDTO(
            total_enquiries=total,
            answered=len(answered),
            answer_rate=(len(answered) / total) if total else 0.0,
            median_response_seconds=(
                int(statistics.median(response_seconds)) if response_seconds else None
            ),
        )
