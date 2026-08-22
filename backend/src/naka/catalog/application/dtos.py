# backend/src/naka/catalog/application/dtos.py
from __future__ import annotations

import uuid
from datetime import time

from pydantic import BaseModel, Field


class DayHoursRequest(BaseModel):
    open_time: time | None = None
    close_time: time | None = None
    midday_break_start: time | None = None
    midday_break_end: time | None = None


class CreateBusinessRequest(BaseModel):
    region_id: uuid.UUID
    locality_id: uuid.UUID
    name_mr: str
    name_en: str
    owner_name: str
    category_ids: list[uuid.UUID]
    contact_numbers: list[str]
    whatsapp_number: str | None = None
    landmark: str
    latitude: float
    longitude: float
    opening_hours: dict[int, DayHoursRequest]
    attributes: list[str] = Field(default_factory=list)


class BusinessDTO(BaseModel):
    id: uuid.UUID
    region_id: uuid.UUID
    locality_id: uuid.UUID
    name_mr: str
    name_en: str
    owner_name: str
    category_ids: list[uuid.UUID]
    contact_numbers: list[str]
    whatsapp_number: str | None
    landmark: str
    latitude: float
    longitude: float
    publication_state: str
