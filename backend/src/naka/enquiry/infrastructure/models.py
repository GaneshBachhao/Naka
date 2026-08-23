# backend/src/naka/enquiry/infrastructure/models.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from naka.shared.infrastructure.database import Base


class RoutedRequestModel(Base):
    __tablename__ = "enquiry_routed_requests"

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enquiry_enquiries.id", ondelete="CASCADE"), primary_key=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessResponseModel(Base):
    __tablename__ = "enquiry_business_responses"

    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("enquiry_enquiries.id", ondelete="CASCADE"), primary_key=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    can_arrange_by: Mapped[date | None] = mapped_column(Date, nullable=True)


class EnquiryModel(Base):
    __tablename__ = "enquiry_enquiries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    customer_phone: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reply_window_seconds: Mapped[int] = mapped_column(Integer)
    # The full ParsedIntent (item_text, confidence, is_advice_request - not
    # just the fields Enquiry promotes to its own columns) so a reload can
    # reconstruct the domain aggregate's parsed_intent field exactly.
    parsed_intent: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    locality_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(16), nullable=True)

    routed_requests: Mapped[list[RoutedRequestModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    responses: Mapped[list[BusinessResponseModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
