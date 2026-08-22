# backend/src/naka/verification/application/dtos.py
from __future__ import annotations

import uuid

from pydantic import BaseModel


class RecordVerificationRequest(BaseModel):
    business_id: uuid.UUID
    tier: str
    method: str
    verified_by: str
    notes: str = ""


class VerificationRecordDTO(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    tier: str
    method: str
    verified_by: str
    notes: str


class ReverificationQueueItemDTO(BaseModel):
    business_id: uuid.UUID
    tier: str
    days_until_decay: int
    is_paying: bool
    is_routable_category: bool
