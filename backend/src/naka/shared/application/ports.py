# backend/src/naka/shared/application/ports.py
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from naka.shared.domain.events import DomainEvent
from naka.shared.domain.phone_number import PhoneNumber


class MessagingPort(Protocol):
    async def send_to_business(self, phone_number: PhoneNumber, message: str) -> None: ...

    async def send_to_customer(self, phone_number: PhoneNumber, message: str) -> None: ...


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
