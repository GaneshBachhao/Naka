# backend/src/naka/enquiry/application/dtos.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class SubmitEnquiryRequest(BaseModel):
    region_id: uuid.UUID
    raw_text: str
    customer_phone: str


class EnquiryDTO(BaseModel):
    id: uuid.UUID
    status: str
    category_id: uuid.UUID | None = None
    locality_id: uuid.UUID | None = None
    routed_business_ids: list[uuid.UUID] = []


class RecordBusinessResponseRequest(BaseModel):
    token: str
    kind: str
    price_paise: int | None = None
    note: str = ""
    can_arrange_by: date | None = None


class RecordBusinessResponseResult(BaseModel):
    outcome: Literal["recorded", "not_found", "expired", "already_responded"]
    was_first: bool = False


class ExpiredEnquirySummary(BaseModel):
    enquiry_id: uuid.UUID


class RoutedRequestPageDTO(BaseModel):
    outcome: Literal["found", "not_found"]
    raw_text: str | None = None
    locality_id: uuid.UUID | None = None
    locality_name: str | None = None
    minutes_ago: int | None = None
    is_expired: bool | None = None
    has_responded: bool | None = None


class EnquiryQueueItemDTO(BaseModel):
    id: uuid.UUID
    status: str
    raw_text: str
    minutes_ago: int


class ParsedIntentDTO(BaseModel):
    category_id: uuid.UUID
    item_text: str
    locality_id: uuid.UUID
    urgency: str
    confidence: float
    is_advice_request: bool


class RoutingSuggestionDTO(BaseModel):
    business_id: uuid.UUID
    distance_km: float
    response_rate: float
    verification_recency_days: int
    reason: str
    default_selected: bool


class RoutedRequestDetailDTO(BaseModel):
    business_id: uuid.UUID
    sent_at: datetime
    expires_at: datetime
    responded_at: datetime | None
    is_expired: bool


class BusinessResponseDetailDTO(BaseModel):
    business_id: uuid.UUID
    kind: str
    price_paise: int | None
    note: str
    can_arrange_by: date | None
    responded_at: datetime


class EnquiryDetailDTO(BaseModel):
    id: uuid.UUID
    status: str
    raw_text: str
    region_id: uuid.UUID
    created_at: datetime
    minutes_ago: int
    parsed_intent: ParsedIntentDTO | None = None
    routed_requests: list[RoutedRequestDetailDTO] = []
    responses: list[BusinessResponseDetailDTO] = []
    winning_business_id: uuid.UUID | None = None


class RouteEnquiryRequest(BaseModel):
    business_ids: list[uuid.UUID]


class RoutedMessageDTO(BaseModel):
    business_id: uuid.UUID
    phone_number: str
    message: str


class RouteEnquiryResult(BaseModel):
    enquiry: EnquiryDTO
    messages: list[RoutedMessageDTO]


class DailyCountersDTO(BaseModel):
    total_enquiries: int
    answered: int
    answer_rate: float
    median_response_seconds: int | None
