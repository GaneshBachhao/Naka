# backend/src/naka/verification/infrastructure/models.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from naka.shared.infrastructure.database import Base


class VerificationRecordModel(Base):
    __tablename__ = "verification_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    tier: Mapped[str] = mapped_column(String(32))
    method: Mapped[str] = mapped_column(String(32))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified_by: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(Text, default="")
