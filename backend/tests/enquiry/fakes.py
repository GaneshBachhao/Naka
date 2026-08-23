# backend/tests/enquiry/fakes.py
from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from naka.enquiry.application.ports import RoutingCandidateContact
from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.services import RoutingCandidate
from naka.enquiry.domain.value_objects import EnquiryStatus, ParsedIntent
from naka.shared.domain.events import DomainEvent
from naka.shared.domain.ids import BusinessId, CategoryId, EnquiryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


class FakeEnquiryRepository:
    def __init__(self, enquiries: list[Enquiry] | None = None) -> None:
        self.by_id: dict[EnquiryId, Enquiry] = {e.id: e for e in (enquiries or [])}

    async def get(self, enquiry_id: EnquiryId) -> Enquiry | None:
        return self.by_id.get(enquiry_id)

    async def get_by_token(self, token: str) -> Enquiry | None:
        for enquiry in self.by_id.values():
            if any(rr.token.value == token for rr in enquiry.routed_requests):
                return enquiry
        return None

    async def add(self, enquiry: Enquiry) -> None:
        self.by_id[enquiry.id] = enquiry

    async def update(self, enquiry: Enquiry) -> None:
        self.by_id[enquiry.id] = enquiry

    async def list_routed(self) -> list[Enquiry]:
        return [e for e in self.by_id.values() if e.status is EnquiryStatus.ROUTED]

    async def list_recent(self, limit: int = 100) -> list[Enquiry]:
        ordered = sorted(self.by_id.values(), key=lambda e: e.created_at, reverse=True)
        return ordered[:limit]

    async def list_since(self, cutoff: dt.datetime) -> list[Enquiry]:
        return [e for e in self.by_id.values() if e.created_at >= cutoff]


class FakeLocalityLookupPort:
    def __init__(self, names: dict[LocalityId, str] | None = None) -> None:
        self.names = names or {}

    async def get_name(self, locality_id: LocalityId) -> str | None:
        return self.names.get(locality_id)


class FakeAIClientPort:
    def __init__(self, intent: ParsedIntent) -> None:
        self.intent = intent
        self.calls: list[tuple[str, RegionId]] = []

    async def parse_enquiry_intent(self, raw_text: str, region_id: RegionId) -> ParsedIntent:
        self.calls.append((raw_text, region_id))
        return self.intent


class FakeRoutingCandidateLookupPort:
    def __init__(self, candidates: list[RoutingCandidateContact] | None = None) -> None:
        self.candidates = candidates or []

    async def find_candidates(
        self, category_id: CategoryId, locality_id: LocalityId
    ) -> list[RoutingCandidateContact]:
        return list(self.candidates)


def make_candidate(
    *,
    business_id: BusinessId,
    distance_km: float = 1.0,
    response_rate: float = 0.5,
    verification_recency_days: int = 10,
    whatsapp_number: str = "9876543210",
) -> RoutingCandidateContact:
    return RoutingCandidateContact(
        candidate=RoutingCandidate(
            business_id=business_id,
            category_matches=True,
            distance_km=distance_km,
            response_rate=response_rate,
            verification_recency_days=verification_recency_days,
        ),
        whatsapp_number=PhoneNumber(whatsapp_number),
    )


class FakeMessaging:
    def __init__(self) -> None:
        self.to_business: list[tuple[PhoneNumber, str]] = []
        self.to_customer: list[tuple[PhoneNumber, str]] = []

    async def send_to_business(self, phone_number: PhoneNumber, message: str) -> None:
        self.to_business.append((phone_number, message))

    async def send_to_customer(self, phone_number: PhoneNumber, message: str) -> None:
        self.to_customer.append((phone_number, message))


class FakeOutbox:
    def __init__(self) -> None:
        self.enqueued: list[DomainEvent] = []

    async def enqueue(self, events: Sequence[DomainEvent]) -> None:
        self.enqueued.extend(events)


class FixedClock:
    def __init__(self, now: dt.datetime) -> None:
        self._now = now

    def now(self) -> dt.datetime:
        return self._now
