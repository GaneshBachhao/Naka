# backend/tests/integration/test_outbox.py
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.domain.ids import BusinessId, VerificationId
from naka.shared.infrastructure.outbox import SqlAlchemyOutbox
from naka.verification.domain.entities import VerificationTier
from naka.verification.domain.events import BusinessVerified

pytestmark = pytest.mark.integration

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


def _event() -> BusinessVerified:
    return BusinessVerified(
        occurred_at=_NOW,
        business_id=BusinessId.new(),
        verification_id=VerificationId.new(),
        tier=VerificationTier.FIELD_VERIFIED,
    )


class TestSqlAlchemyOutbox:
    async def test_enqueued_event_is_pending_and_serialized(self, db_session: AsyncSession) -> None:
        outbox = SqlAlchemyOutbox(db_session)
        event = _event()

        await outbox.enqueue((event,))
        await db_session.flush()

        pending = await outbox.drain_pending(now=_NOW)
        assert len(pending) == 1
        row = pending[0]
        assert row.event_type == "BusinessVerified"
        # dataclasses.asdict() recurses into BusinessId's own `value: UUID`
        # field too, so it lands as a nested object, not a bare string.
        assert row.payload["business_id"] == {"value": str(event.business_id.value)}
        assert row.payload["tier"] == "field_verified"

    async def test_drain_marks_events_dispatched_and_does_not_return_them_again(
        self, db_session: AsyncSession
    ) -> None:
        outbox = SqlAlchemyOutbox(db_session)
        await outbox.enqueue((_event(),))
        await db_session.flush()

        first_drain = await outbox.drain_pending(now=_NOW)
        await db_session.flush()
        second_drain = await outbox.drain_pending(now=_NOW)

        assert len(first_drain) == 1
        assert second_drain == []

    async def test_drain_respects_limit(self, db_session: AsyncSession) -> None:
        outbox = SqlAlchemyOutbox(db_session)
        await outbox.enqueue((_event(), _event(), _event()))
        await db_session.flush()

        pending = await outbox.drain_pending(now=_NOW, limit=2)
        assert len(pending) == 2
