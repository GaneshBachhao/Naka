# backend/src/naka/shared/infrastructure/outbox.py
from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from sqlalchemy import DateTime, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from naka.shared.domain.events import DomainEvent
from naka.shared.infrastructure.database import Base


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _json_default(value: object) -> object:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {value!r} for the outbox")


def _event_to_payload(event: DomainEvent) -> dict[str, Any]:
    # dataclasses.asdict() recurses into EntityId's own `value: UUID` field
    # too, leaving raw UUIDs behind for json.dumps' `default=` to catch.
    # StrEnum fields need no help - they're already str subclasses.
    raw = {key: value for key, value in dataclasses.asdict(event).items() if key != "occurred_at"}
    return cast(dict[str, Any], json.loads(json.dumps(raw, default=_json_default)))


class SqlAlchemyOutbox:
    """Transactional outbox: enqueue() runs in the same session/transaction
    as the use case's aggregate persistence, so an event is never recorded
    without its state change (or vice versa). Nothing consumes these events
    yet - draining currently just marks them dispatched; real handlers are
    future work, wired in once a first cross-context reaction actually
    needs one (see T4's note on BusinessVerified)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            self._session.add(
                OutboxEventModel(
                    id=uuid.uuid4(),
                    event_type=event.__class__.__name__,
                    payload=_event_to_payload(event),
                    occurred_at=event.occurred_at,
                )
            )

    async def drain_pending(self, *, now: datetime, limit: int = 100) -> list[OutboxEventModel]:
        stmt = (
            select(OutboxEventModel)
            .where(OutboxEventModel.dispatched_at.is_(None))
            .order_by(OutboxEventModel.occurred_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        pending = list(result.scalars().all())
        for row in pending:
            row.dispatched_at = now
        return pending
