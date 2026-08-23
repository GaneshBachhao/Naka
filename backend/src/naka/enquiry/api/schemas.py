# backend/src/naka/enquiry/api/schemas.py
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class RecordResponseBody(BaseModel):
    """POST /r/{token}'s body - token itself comes from the URL path, not
    the body, so this is a narrower shape than the application layer's
    RecordBusinessResponseRequest (which is built by combining the two)."""

    kind: str
    price_paise: int | None = None
    note: str = ""
    can_arrange_by: date | None = None


class OperatorQueueMessageSchema(BaseModel):
    id: uuid.UUID
    recipient_kind: str
    phone_number: str
    message: str
    created_at: datetime
    sent_at: datetime | None
