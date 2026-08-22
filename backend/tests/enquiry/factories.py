# backend/tests/enquiry/factories.py
from __future__ import annotations

import dataclasses
import datetime as dt

from naka.enquiry.domain.entities import BusinessResponse, Enquiry, RoutedRequest
from naka.enquiry.domain.value_objects import (
    EnquiryStatus,
    ParsedIntent,
    ResponseKind,
    RoutingToken,
    Urgency,
)
from naka.shared.domain.ids import BusinessId, CategoryId, EnquiryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber

NOW = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)


def make_parsed_intent(**overrides: object) -> ParsedIntent:
    intent = ParsedIntent(
        category_id=CategoryId.new(),
        item_text="pesticide for cotton crop",
        locality_id=LocalityId.new(),
        urgency=Urgency.NORMAL,
        confidence=0.9,
        is_advice_request=False,
    )
    return dataclasses.replace(intent, **overrides) if overrides else intent


def make_received_enquiry(**overrides: object) -> Enquiry:
    enquiry, _ = Enquiry.receive(
        id=EnquiryId.new(),
        region_id=RegionId.new(),
        raw_text="कापसासाठी औषध कोणाकडे आहे?",
        customer_phone=PhoneNumber("9876543210"),
        created_at=NOW,
    )
    return dataclasses.replace(enquiry, **overrides) if overrides else enquiry


def make_parsed_enquiry(**overrides: object) -> Enquiry:
    enquiry = make_received_enquiry()
    parsed, _ = enquiry.apply_parsed_intent(make_parsed_intent(), NOW)
    return dataclasses.replace(parsed, **overrides) if overrides else parsed


def make_routed_enquiry(
    business_ids: tuple[BusinessId, ...] | None = None, **overrides: object
) -> Enquiry:
    enquiry = make_parsed_enquiry()
    ids = business_ids or (BusinessId.new(), BusinessId.new(), BusinessId.new())
    routed, _ = enquiry.route(ids, NOW)
    return dataclasses.replace(routed, **overrides) if overrides else routed


def make_routed_request(**overrides: object) -> RoutedRequest:
    request = RoutedRequest(
        enquiry_id=EnquiryId.new(),
        business_id=BusinessId.new(),
        token=RoutingToken.new(),
        sent_at=NOW,
        expires_at=NOW + dt.timedelta(minutes=30),
    )
    return dataclasses.replace(request, **overrides) if overrides else request


def make_response(**overrides: object) -> BusinessResponse:
    response = BusinessResponse(
        business_id=BusinessId.new(),
        kind=ResponseKind.HAVE_IT,
        responded_at=NOW + dt.timedelta(minutes=5),
    )
    return dataclasses.replace(response, **overrides) if overrides else response


__all__ = [
    "NOW",
    "EnquiryStatus",
    "make_parsed_intent",
    "make_received_enquiry",
    "make_parsed_enquiry",
    "make_routed_enquiry",
    "make_routed_request",
    "make_response",
]
