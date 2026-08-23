# backend/tests/integration/test_manual_messaging.py
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.domain.phone_number import PhoneNumber
from naka.shared.infrastructure.messaging import ManualMessagingAdapter, OperatorQueueMessageModel

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
