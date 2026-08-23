# backend/src/naka/shared/application/use_cases.py
from __future__ import annotations

import uuid

from naka.shared.application.ports import Clock, OperatorQueueMessage, OperatorQueuePort


class ListOperatorQueue:
    def __init__(self, queue: OperatorQueuePort) -> None:
        self._queue = queue

    async def execute(self) -> list[OperatorQueueMessage]:
        return await self._queue.list_pending()


class MarkOperatorMessageSent:
    def __init__(self, queue: OperatorQueuePort, clock: Clock) -> None:
        self._queue = queue
        self._clock = clock

    async def execute(self, message_id: uuid.UUID) -> None:
        await self._queue.mark_sent(message_id, self._clock.now())
