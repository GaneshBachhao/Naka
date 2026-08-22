# backend/src/naka/enquiry/application/dtos.py
from __future__ import annotations

import uuid
from datetime import date
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
