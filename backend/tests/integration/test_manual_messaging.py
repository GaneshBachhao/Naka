# backend/tests/integration/test_manual_messaging.py
from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.domain.phone_number import PhoneNumber
from naka.shared.infrastructure.messaging import (
    ManualMessagingAdapter,
    OperatorQueueMessageModel,
    SqlAlchemyOperatorQueue,
)

pytestmark = pytest.mark.integration

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


class _FixedClock:
    def now(self) -> dt.datetime:
        return _NOW


class TestManualMessagingAdapter:
    async def test_send_to_business_writes_operator_queue_row(
        self, db_session: AsyncSession
    ) -> None:
        adapter = ManualMessagingAdapter(db_session, _FixedClock())
        phone = PhoneNumber("9876543210")

        await adapter.send_to_business(phone, "New enquiry: pesticide for cotton")
        await db_session.flush()

        rows = (await db_session.execute(select(OperatorQueueMessageModel))).scalars().all()
        assert len(rows) == 1
        assert rows[0].recipient_kind == "business"
        assert rows[0].phone_number == "9876543210"
        assert rows[0].sent_at is None

    async def test_send_to_customer_writes_operator_queue_row(
        self, db_session: AsyncSession
    ) -> None:
        adapter = ManualMessagingAdapter(db_session, _FixedClock())
        phone = PhoneNumber("9876543210")

        await adapter.send_to_customer(phone, "Someone has what you asked about")
        await db_session.flush()

        rows = (await db_session.execute(select(OperatorQueueMessageModel))).scalars().all()
        assert len(rows) == 1
        assert rows[0].recipient_kind == "customer"


class TestSqlAlchemyOperatorQueue:
    async def test_list_pending_excludes_sent_messages(self, db_session: AsyncSession) -> None:
        messaging = ManualMessagingAdapter(db_session, _FixedClock())
        await messaging.send_to_business(PhoneNumber("9876543210"), "pending one")
        await messaging.send_to_business(PhoneNumber("9876543211"), "will be marked sent")
        await db_session.flush()

        queue = SqlAlchemyOperatorQueue(db_session)
        [to_mark, _pending] = await queue.list_pending()
        await queue.mark_sent(to_mark.id, _NOW + dt.timedelta(minutes=1))
        await db_session.flush()
        db_session.expunge_all()

        remaining = await SqlAlchemyOperatorQueue(db_session).list_pending()
        assert len(remaining) == 1
        assert remaining[0].id != to_mark.id

    async def test_mark_sent_on_unknown_id_is_a_no_op(self, db_session: AsyncSession) -> None:
        queue = SqlAlchemyOperatorQueue(db_session)
        await queue.mark_sent(uuid.uuid4(), _NOW)  # must not raise
