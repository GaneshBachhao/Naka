# backend/src/naka/shared/infrastructure/messaging.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from naka.shared.application.ports import Clock
from naka.shared.domain.phone_number import PhoneNumber
from naka.shared.infrastructure.database import Base


class OperatorQueueMessageModel(Base):
    __tablename__ = "operator_queue_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    recipient_kind: Mapped[str] = mapped_column(String(16))  # "business" | "customer"
    phone_number: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManualMessagingAdapter:
    """Wizard-of-Oz MessagingPort: writes to an operator queue table instead
    of calling WhatsApp directly. T8's ops console reads this queue and
    shows the operator the exact message to copy and send by hand.
    WhatsAppMessagingAdapter replaces this later with zero changes above
    Infrastructure - if that swap ever needs to touch Application or
    Domain, this port was the wrong shape."""

    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def send_to_business(self, phone_number: PhoneNumber, message: str) -> None:
        await self._enqueue("business", phone_number, message)

    async def send_to_customer(self, phone_number: PhoneNumber, message: str) -> None:
        await self._enqueue("customer", phone_number, message)

    async def _enqueue(self, recipient_kind: str, phone_number: PhoneNumber, message: str) -> None:
        self._session.add(
            OperatorQueueMessageModel(
                id=uuid.uuid4(),
                recipient_kind=recipient_kind,
                phone_number=phone_number.value,
                message=message,
                created_at=self._clock.now(),
            )
        )
