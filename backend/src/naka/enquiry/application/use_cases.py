# backend/src/naka/enquiry/application/use_cases.py
from __future__ import annotations

from naka.enquiry.application.dtos import (
    EnquiryDTO,
    ExpiredEnquirySummary,
    RecordBusinessResponseRequest,
    RecordBusinessResponseResult,
    SubmitEnquiryRequest,
)
from naka.enquiry.application.errors import EnquiryNotFoundError, InsufficientRoutingCandidatesError
from naka.enquiry.application.ports import (
    AIClientPort,
    EnquiryRepository,
    RoutingCandidateLookupPort,
)
from naka.enquiry.domain.entities import BusinessResponse, Enquiry
from naka.enquiry.domain.events import EnquiryAnswered
from naka.enquiry.domain.services import select_businesses_for_routing
from naka.enquiry.domain.value_objects import EnquiryStatus, ResponseKind
from naka.shared.application.ports import Clock, MessagingPort, OutboxPort
from naka.shared.domain.ids import EnquiryId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


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


class ParseAndRouteEnquiry:
    def __init__(
        self,
        enquiries: EnquiryRepository,
        ai_client: AIClientPort,
        candidates: RoutingCandidateLookupPort,
        messaging: MessagingPort,
        outbox: OutboxPort,
        clock: Clock,
        response_link_base_url: str,
    ) -> None:
        self._enquiries = enquiries
        self._ai_client = ai_client
        self._candidates = candidates
        self._messaging = messaging
        self._outbox = outbox
        self._clock = clock
        self._response_link_base_url = response_link_base_url

    async def execute(self, enquiry_id: EnquiryId) -> EnquiryDTO:
        enquiry = await self._enquiries.get(enquiry_id)
        if enquiry is None:
            raise EnquiryNotFoundError(enquiry_id)

        intent = await self._ai_client.parse_enquiry_intent(enquiry.raw_text, enquiry.region_id)
        now = self._clock.now()
        parsed, parse_events = enquiry.apply_parsed_intent(intent, now)
        await self._enquiries.update(parsed)
        await self._outbox.enqueue(parse_events)

        if parsed.status is EnquiryStatus.DEFLECTED:
            return _to_dto(parsed)

        # apply_parsed_intent() sets category_id/locality_id together with
        # PARSED whenever the enquiry isn't deflected - guaranteed by the
        # domain, not statically visible to mypy from the dataclass's
        # Optional fields.
        assert parsed.category_id is not None
        assert parsed.locality_id is not None

        found = await self._candidates.find_candidates(parsed.category_id, parsed.locality_id)
        contact_by_business = {c.candidate.business_id: c.whatsapp_number for c in found}
        business_ids = select_businesses_for_routing(c.candidate for c in found)
        if len(business_ids) < 3:
            raise InsufficientRoutingCandidatesError(enquiry_id)

        routed, route_events = parsed.route(business_ids, now)
        await self._enquiries.update(routed)
        await self._outbox.enqueue(route_events)

        for routed_request in routed.routed_requests:
            phone_number = contact_by_business[routed_request.business_id]
            link = f"{self._response_link_base_url}/{routed_request.token.value}"
            message = f"{routed.raw_text}\n{link}"
            await self._messaging.send_to_business(phone_number, message)

        return _to_dto(routed)


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
