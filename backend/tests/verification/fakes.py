# backend/tests/verification/fakes.py
from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from naka.shared.domain.events import DomainEvent
from naka.shared.domain.ids import BusinessId
from naka.verification.application.ports import ReverificationSignals
from naka.verification.domain.entities import VerificationRecord


class FakeVerificationRecordRepository:
    def __init__(self, records: list[VerificationRecord] | None = None) -> None:
        self.records: list[VerificationRecord] = records or []

    async def add(self, record: VerificationRecord) -> None:
        self.records.append(record)

    async def list_latest_per_business(self) -> list[VerificationRecord]:
        return list(self.records)


class FakeReverificationSignalsPort:
    def __init__(self, signals: dict[BusinessId, ReverificationSignals] | None = None) -> None:
        self.signals = signals or {}

    async def get_signals(
        self, business_ids: Sequence[BusinessId]
    ) -> dict[BusinessId, ReverificationSignals]:
        return {
            business_id: self.signals.get(
                business_id, ReverificationSignals(is_paying=False, is_routable_category=False)
            )
            for business_id in business_ids
        }


class FakeOutbox:
    def __init__(self) -> None:
        self.enqueued: list[DomainEvent] = []

    async def enqueue(self, events: Sequence[DomainEvent]) -> None:
        self.enqueued.extend(events)


class FixedClock:
    def __init__(self, now: dt.datetime) -> None:
        self._now = now

    def now(self) -> dt.datetime:
        return self._now
