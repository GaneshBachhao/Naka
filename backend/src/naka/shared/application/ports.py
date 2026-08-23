# backend/src/naka/shared/application/ports.py
from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from naka.shared.domain.events import DomainEvent
from naka.shared.domain.phone_number import PhoneNumber


class MessagingPort(Protocol):
    async def send_to_business(self, phone_number: PhoneNumber, message: str) -> None: ...

    async def send_to_customer(self, phone_number: PhoneNumber, message: str) -> None: ...


@dataclass(frozen=True)
class OperatorQueueMessage:
    id: uuid.UUID
    recipient_kind: str
    phone_number: str
    message: str
    created_at: datetime
    sent_at: datetime | None


class OperatorQueuePort(Protocol):
    """The read/manage side of the Wizard-of-Oz operator queue that
    MessagingPort's ManualMessagingAdapter writes to. T8's ops console (and,
    ahead of that, T6's ops API) uses this to show the operator what's
    pending and let them mark a message sent once they've actually copied
    and sent it by hand."""

    async def list_pending(self) -> list[OperatorQueueMessage]: ...

    async def mark_sent(self, message_id: uuid.UUID, sent_at: datetime) -> None: ...


class OutboxPort(Protocol):
    """Transactional outbox: use cases enqueue events here in the same
    transaction as their state change. Infrastructure (T5) drains the
    outbox via an ARQ worker - domain events don't reach any adapter
    directly from the application layer."""

    async def enqueue(self, events: Sequence[DomainEvent]) -> None: ...


class Clock(Protocol):
    """Injected rather than calling datetime.now(UTC) directly, so every
    use case is deterministically testable without patching global state."""

    def now(self) -> datetime: ...
