# backend/src/naka/enquiry/application/ports.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.services import RoutingCandidate
from naka.enquiry.domain.value_objects import ParsedIntent
from naka.shared.domain.ids import CategoryId, EnquiryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


class EnquiryRepository(Protocol):
    async def get(self, enquiry_id: EnquiryId) -> Enquiry | None: ...

    async def get_by_token(self, token: str) -> Enquiry | None: ...

    async def add(self, enquiry: Enquiry) -> None: ...

    async def update(self, enquiry: Enquiry) -> None: ...

    async def list_routed(self) -> list[Enquiry]: ...

    async def list_recent(self, limit: int = 100) -> list[Enquiry]: ...

    async def list_since(self, cutoff: datetime) -> list[Enquiry]: ...


class AIClientPort(Protocol):
    async def parse_enquiry_intent(self, raw_text: str, region_id: RegionId) -> ParsedIntent: ...


class LocalityLookupPort(Protocol):
    """The dealer response page (GET /r/{token}) needs to show which
    village the customer is in, but Enquiry only stores locality_id -
    resolving it to a display name means reaching into catalog, which
    enquiry's domain can't do itself. Returns just the name, not catalog's
    Locality entity - CLAUDE.md's "never import another context's domain
    objects" applies at the application layer too, not only inside
    domain/; the implementing adapter (enquiry/infrastructure) is where
    catalog.domain.Locality is allowed to appear, since only Infrastructure
    is exempt from context isolation."""

    async def get_name(self, locality_id: LocalityId) -> str | None: ...


@dataclass(frozen=True)
class RoutingCandidateContact:
    """A RoutingCandidate carries only the ranking signals - it's a pure
    domain value object, unaware of contact details. Messaging a selected
    business needs its WhatsApp number too, so the port pairs the two here
    rather than teaching the domain service about contact info."""

    candidate: RoutingCandidate
    whatsapp_number: PhoneNumber


class RoutingCandidateLookupPort(Protocol):
    """Hides the cross-context assembly select_businesses_for_routing's
    input needs - eligible (catalog) businesses in the right category and
    locality, with their distance/response-rate/verification-recency
    signals. Enquiry's application layer only knows this port's shape."""

    async def find_candidates(
        self, category_id: CategoryId, locality_id: LocalityId
    ) -> list[RoutingCandidateContact]: ...
