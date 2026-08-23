# backend/tests/shared/test_use_cases.py
from __future__ import annotations

import datetime as dt
import uuid

from naka.shared.application.ports import OperatorQueueMessage
from naka.shared.application.use_cases import ListOperatorQueue, MarkOperatorMessageSent
from tests.shared.fakes import FakeOperatorQueue, FixedClock

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


def _message(**overrides: object) -> OperatorQueueMessage:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        recipient_kind="business",
        phone_number="9876543210",
        message="New enquiry: pesticide for cotton",
        created_at=_NOW,
        sent_at=None,
    )
    defaults.update(overrides)
    return OperatorQueueMessage(**defaults)  # type: ignore[arg-type]


class TestListOperatorQueue:
    async def test_returns_only_pending_messages(self) -> None:
        pending = _message()
        already_sent = _message(sent_at=_NOW)
        queue = FakeOperatorQueue([pending, already_sent])

        result = await ListOperatorQueue(queue).execute()

        assert [m.id for m in result] == [pending.id]


class TestMarkOperatorMessageSent:
    async def test_marks_the_message_sent(self) -> None:
        message = _message()
        queue = FakeOperatorQueue([message])

        await MarkOperatorMessageSent(queue, FixedClock(_NOW)).execute(message.id)

        assert queue.messages[0].sent_at == _NOW

    async def test_is_a_no_op_for_an_unknown_message(self) -> None:
        queue = FakeOperatorQueue([])
        await MarkOperatorMessageSent(queue, FixedClock(_NOW)).execute(uuid.uuid4())
        assert queue.messages == []
