# backend/src/naka/enquiry/domain/entities.py
from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from naka.enquiry.domain.events import (
    AdviceRequestDeflected,
    EnquiryAnswered,
    EnquiryReceived,
    EnquiryRouted,
    EnquiryUnanswered,
    ResponseReceived,
)
from naka.enquiry.domain.value_objects import (
    EnquiryStatus,
    ParsedIntent,
    ResponseKind,
    RoutingToken,
    Urgency,
)
from naka.shared.domain.events import DomainEvent
from naka.shared.domain.ids import BusinessId, CategoryId, EnquiryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber

_DEFAULT_REPLY_WINDOW = timedelta(minutes=30)


@dataclass(frozen=True)
class BusinessResponse:
    business_id: BusinessId
    kind: ResponseKind
    responded_at: datetime
    price_paise: int | None = None
    note: str = ""
    can_arrange_by: date | None = None

    def __post_init__(self) -> None:
        if self.responded_at.tzinfo is None:
            raise ValueError("responded_at must be timezone-aware")
        if self.price_paise is not None and self.price_paise < 0:
            raise ValueError("price_paise must not be negative")
        if self.kind is ResponseKind.CAN_ARRANGE_BY and self.can_arrange_by is None:
            raise ValueError("CAN_ARRANGE_BY requires can_arrange_by")
        if self.kind is not ResponseKind.CAN_ARRANGE_BY and self.can_arrange_by is not None:
            raise ValueError("can_arrange_by is only valid for CAN_ARRANGE_BY responses")


@dataclass(frozen=True)
class RoutedRequest:
    enquiry_id: EnquiryId
    business_id: BusinessId
    token: RoutingToken
    sent_at: datetime
    expires_at: datetime
    responded_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.sent_at.tzinfo is None:
            raise ValueError("sent_at must be timezone-aware")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at <= self.sent_at:
            raise ValueError("expires_at must be after sent_at")
        if self.responded_at is not None and self.responded_at.tzinfo is None:
            raise ValueError("responded_at must be timezone-aware")

    @property
    def has_responded(self) -> bool:
        return self.responded_at is not None

    def is_expired_at(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now >= self.expires_at

    def is_settled_at(self, now: datetime) -> bool:
        return self.has_responded or self.is_expired_at(now)


@dataclass(frozen=True)
class Enquiry:
    id: EnquiryId
    region_id: RegionId
    raw_text: str
    customer_phone: PhoneNumber
    status: EnquiryStatus
    created_at: datetime
    reply_window: timedelta = _DEFAULT_REPLY_WINDOW
    parsed_intent: ParsedIntent | None = None
    locality_id: LocalityId | None = None
    category_id: CategoryId | None = None
    urgency: Urgency | None = None
    routed_requests: tuple[RoutedRequest, ...] = ()
    responses: tuple[BusinessResponse, ...] = ()

    def __post_init__(self) -> None:
        if not self.raw_text.strip():
            raise ValueError("raw_text must not be empty")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

    @classmethod
    def receive(
        cls,
        *,
        id: EnquiryId,
        region_id: RegionId,
        raw_text: str,
        customer_phone: PhoneNumber,
        created_at: datetime,
        reply_window: timedelta = _DEFAULT_REPLY_WINDOW,
    ) -> tuple[Enquiry, tuple[DomainEvent, ...]]:
        enquiry = cls(
            id=id,
            region_id=region_id,
            raw_text=raw_text,
            customer_phone=customer_phone,
            status=EnquiryStatus.RECEIVED,
            created_at=created_at,
            reply_window=reply_window,
        )
        event = EnquiryReceived(occurred_at=created_at, enquiry_id=id, region_id=region_id)
        return enquiry, (event,)

    def apply_parsed_intent(
        self, intent: ParsedIntent, now: datetime
    ) -> tuple[Enquiry, tuple[DomainEvent, ...]]:
        if self.status is not EnquiryStatus.RECEIVED:
            raise ValueError(f"cannot parse an enquiry that is {self.status}")

        if intent.is_advice_request:
            # The Insecticides Act / medical-advice boundary from CLAUDE.md:
            # an advice request is deflected here, in the domain, and never
            # reaches routing - not a prompt-level filter that could be
            # bypassed by a parsing edge case.
            updated = dataclasses.replace(
                self, parsed_intent=intent, status=EnquiryStatus.DEFLECTED
            )
            return updated, (AdviceRequestDeflected(occurred_at=now, enquiry_id=self.id),)

        updated = dataclasses.replace(
            self,
            parsed_intent=intent,
            locality_id=intent.locality_id,
            category_id=intent.category_id,
            urgency=intent.urgency,
            status=EnquiryStatus.PARSED,
        )
        return updated, ()

    def route(
        self, business_ids: Sequence[BusinessId], now: datetime
    ) -> tuple[Enquiry, tuple[DomainEvent, ...]]:
        if self.status is not EnquiryStatus.PARSED:
            raise ValueError(f"cannot route an enquiry that is {self.status}")
        if not 3 <= len(business_ids) <= 5:
            raise ValueError("fan-out must route to between 3 and 5 businesses")

        routed = tuple(
            RoutedRequest(
                enquiry_id=self.id,
                business_id=business_id,
                token=RoutingToken.new(),
                sent_at=now,
                expires_at=now + self.reply_window,
            )
            for business_id in business_ids
        )
        updated = dataclasses.replace(self, status=EnquiryStatus.ROUTED, routed_requests=routed)
        event = EnquiryRouted(occurred_at=now, enquiry_id=self.id, business_ids=tuple(business_ids))
        return updated, (event,)

    @property
    def winning_response(self) -> BusinessResponse | None:
        # First HAVE_IT in recording order wins - record_response() appends in
        # the order calls arrive, so this is "first processed", not "earliest
        # responded_at". That's deliberate: recording order is what this
        # aggregate can actually guarantee deterministically; a client-supplied
        # timestamp could be skewed or arrive out of order.
        return next((r for r in self.responses if r.kind is ResponseKind.HAVE_IT), None)

    def record_response(
        self, response: BusinessResponse, now: datetime
    ) -> tuple[Enquiry, tuple[DomainEvent, ...]]:
        if self.status not in (EnquiryStatus.ROUTED, EnquiryStatus.ANSWERED):
            raise ValueError(f"cannot record a response while enquiry is {self.status}")

        matching = next(
            (rr for rr in self.routed_requests if rr.business_id == response.business_id), None
        )
        if matching is None:
            raise ValueError("response.business_id was never routed for this enquiry")
        if matching.has_responded:
            raise ValueError("this business has already responded")

        updated_routed = tuple(
            (
                dataclasses.replace(rr, responded_at=response.responded_at)
                if rr.business_id == response.business_id
                else rr
            )
            for rr in self.routed_requests
        )

        is_first_have_it = response.kind is ResponseKind.HAVE_IT and self.winning_response is None
        new_status = EnquiryStatus.ANSWERED if is_first_have_it else self.status
        updated = dataclasses.replace(
            self,
            routed_requests=updated_routed,
            responses=(*self.responses, response),
            status=new_status,
        )

        events: tuple[DomainEvent, ...] = (
            ResponseReceived(
                occurred_at=now,
                enquiry_id=self.id,
                business_id=response.business_id,
                kind=response.kind,
            ),
        )
        if is_first_have_it:
            events += (
                EnquiryAnswered(
                    occurred_at=now, enquiry_id=self.id, winning_business_id=response.business_id
                ),
            )
        return updated, events

    def expire(self, now: datetime) -> tuple[Enquiry, tuple[DomainEvent, ...]]:
        # Called speculatively by a periodic sweep over every ROUTED enquiry
        # (T5's expire_enquiry_windows job), so "not due yet" is a normal
        # no-op here rather than an error - unlike the transitions above,
        # whose callers already know, and must be right about, the enquiry's
        # state before calling.
        if self.status is not EnquiryStatus.ROUTED:
            return self, ()
        all_settled = all(rr.is_settled_at(now) for rr in self.routed_requests)
        if not self.routed_requests or not all_settled:
            return self, ()
        updated = dataclasses.replace(self, status=EnquiryStatus.UNANSWERED)
        return updated, (EnquiryUnanswered(occurred_at=now, enquiry_id=self.id),)
