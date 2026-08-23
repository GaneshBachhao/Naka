# backend/src/naka/enquiry/infrastructure/mappers.py
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from naka.enquiry.domain.entities import BusinessResponse, Enquiry, RoutedRequest
from naka.enquiry.domain.value_objects import (
    EnquiryStatus,
    ParsedIntent,
    ResponseKind,
    RoutingToken,
    Urgency,
)
from naka.enquiry.infrastructure.models import (
    BusinessResponseModel,
    EnquiryModel,
    RoutedRequestModel,
)
from naka.shared.domain.ids import BusinessId, CategoryId, EnquiryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


def _parsed_intent_to_json(intent: ParsedIntent) -> dict[str, Any]:
    return {
        "category_id": str(intent.category_id.value),
        "item_text": intent.item_text,
        "locality_id": str(intent.locality_id.value),
        "urgency": intent.urgency.value,
        "confidence": intent.confidence,
        "is_advice_request": intent.is_advice_request,
    }


def _parsed_intent_from_json(data: dict[str, Any]) -> ParsedIntent:
    return ParsedIntent(
        category_id=CategoryId(uuid.UUID(data["category_id"])),
        item_text=data["item_text"],
        locality_id=LocalityId(uuid.UUID(data["locality_id"])),
        urgency=Urgency(data["urgency"]),
        confidence=data["confidence"],
        is_advice_request=data["is_advice_request"],
    )


def routed_request_to_domain(model: RoutedRequestModel) -> RoutedRequest:
    return RoutedRequest(
        enquiry_id=EnquiryId(model.enquiry_id),
        business_id=BusinessId(model.business_id),
        token=RoutingToken(model.token),
        sent_at=model.sent_at,
        expires_at=model.expires_at,
        responded_at=model.responded_at,
    )


def routed_request_to_model(routed_request: RoutedRequest) -> RoutedRequestModel:
    return RoutedRequestModel(
        enquiry_id=routed_request.enquiry_id.value,
        business_id=routed_request.business_id.value,
        token=routed_request.token.value,
        sent_at=routed_request.sent_at,
        expires_at=routed_request.expires_at,
        responded_at=routed_request.responded_at,
    )


def response_to_domain(model: BusinessResponseModel) -> BusinessResponse:
    return BusinessResponse(
        business_id=BusinessId(model.business_id),
        kind=ResponseKind(model.kind),
        responded_at=model.responded_at,
        price_paise=model.price_paise,
        note=model.note,
        can_arrange_by=model.can_arrange_by,
    )


def response_to_model(enquiry_id: EnquiryId, response: BusinessResponse) -> BusinessResponseModel:
    return BusinessResponseModel(
        enquiry_id=enquiry_id.value,
        business_id=response.business_id.value,
        kind=response.kind.value,
        responded_at=response.responded_at,
        price_paise=response.price_paise,
        note=response.note,
        can_arrange_by=response.can_arrange_by,
    )


def enquiry_to_domain(model: EnquiryModel) -> Enquiry:
    return Enquiry(
        id=EnquiryId(model.id),
        region_id=RegionId(model.region_id),
        raw_text=model.raw_text,
        customer_phone=PhoneNumber(model.customer_phone),
        status=EnquiryStatus(model.status),
        created_at=model.created_at,
        reply_window=timedelta(seconds=model.reply_window_seconds),
        parsed_intent=(
            _parsed_intent_from_json(model.parsed_intent) if model.parsed_intent else None
        ),
        locality_id=LocalityId(model.locality_id) if model.locality_id else None,
        category_id=CategoryId(model.category_id) if model.category_id else None,
        urgency=Urgency(model.urgency) if model.urgency else None,
        routed_requests=tuple(routed_request_to_domain(rr) for rr in model.routed_requests),
        responses=tuple(response_to_domain(r) for r in model.responses),
    )


def enquiry_to_model(enquiry: Enquiry) -> EnquiryModel:
    return EnquiryModel(
        id=enquiry.id.value,
        region_id=enquiry.region_id.value,
        raw_text=enquiry.raw_text,
        customer_phone=enquiry.customer_phone.value,
        status=enquiry.status.value,
        created_at=enquiry.created_at,
        reply_window_seconds=int(enquiry.reply_window.total_seconds()),
        parsed_intent=(
            _parsed_intent_to_json(enquiry.parsed_intent) if enquiry.parsed_intent else None
        ),
        category_id=enquiry.category_id.value if enquiry.category_id else None,
        locality_id=enquiry.locality_id.value if enquiry.locality_id else None,
        urgency=enquiry.urgency.value if enquiry.urgency else None,
        routed_requests=[routed_request_to_model(rr) for rr in enquiry.routed_requests],
        responses=[response_to_model(enquiry.id, r) for r in enquiry.responses],
    )
