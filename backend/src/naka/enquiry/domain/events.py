# backend/src/naka/enquiry/domain/events.py
from __future__ import annotations

from dataclasses import dataclass

from naka.enquiry.domain.value_objects import ResponseKind
from naka.shared.domain.events import DomainEvent
from naka.shared.domain.ids import BusinessId, EnquiryId, RegionId


@dataclass(frozen=True)
class EnquiryReceived(DomainEvent):
    enquiry_id: EnquiryId
    region_id: RegionId


@dataclass(frozen=True)
class EnquiryRouted(DomainEvent):
    enquiry_id: EnquiryId
    business_ids: tuple[BusinessId, ...]


@dataclass(frozen=True)
class ResponseReceived(DomainEvent):
    enquiry_id: EnquiryId
    business_id: BusinessId
    kind: ResponseKind


@dataclass(frozen=True)
class EnquiryAnswered(DomainEvent):
    enquiry_id: EnquiryId
    winning_business_id: BusinessId


@dataclass(frozen=True)
class EnquiryUnanswered(DomainEvent):
    enquiry_id: EnquiryId


@dataclass(frozen=True)
class AdviceRequestDeflected(DomainEvent):
    enquiry_id: EnquiryId
