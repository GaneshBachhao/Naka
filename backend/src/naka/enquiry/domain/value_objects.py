# backend/src/naka/enquiry/domain/value_objects.py
from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum

from naka.shared.domain.ids import CategoryId, LocalityId


class Urgency(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"


class EnquiryStatus(StrEnum):
    RECEIVED = "received"
    PARSED = "parsed"
    ROUTED = "routed"
    ANSWERED = "answered"
    UNANSWERED = "unanswered"
    DEFLECTED = "deflected"
    CLOSED = "closed"


class ResponseKind(StrEnum):
    HAVE_IT = "have_it"
    DONT_HAVE = "dont_have"
    CAN_ARRANGE_BY = "can_arrange_by"


@dataclass(frozen=True)
class RoutingToken:
    value: str

    @classmethod
    def new(cls) -> RoutingToken:
        return cls(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class ParsedIntent:
    category_id: CategoryId
    item_text: str
    locality_id: LocalityId
    urgency: Urgency
    confidence: float
    is_advice_request: bool

    def __post_init__(self) -> None:
        if not self.item_text.strip():
            raise ValueError("item_text must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be within 0.0..1.0: {self.confidence}")
