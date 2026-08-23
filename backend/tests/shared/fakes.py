# backend/tests/shared/fakes.py
from __future__ import annotations

import datetime as dt
import uuid

from naka.shared.application.ports import OperatorQueueMessage


class FakeOperatorQueue:
    def __init__(self, messages: list[OperatorQueueMessage] | None = None) -> None:
        self.messages: list[OperatorQueueMessage] = messages or []

    async def list_pending(self) -> list[OperatorQueueMessage]:
        return [m for m in self.messages if m.sent_at is None]

    async def mark_sent(self, message_id: uuid.UUID, sent_at: dt.datetime) -> None:
        self.messages = [
            (
                OperatorQueueMessage(
                    id=m.id,
                    recipient_kind=m.recipient_kind,
                    phone_number=m.phone_number,
                    message=m.message,
                    created_at=m.created_at,
                    sent_at=sent_at,
                )
                if m.id == message_id
                else m
            )
            for m in self.messages
        ]


class FixedClock:
    def __init__(self, now: dt.datetime) -> None:
        self._now = now

    def now(self) -> dt.datetime:
        return self._now
