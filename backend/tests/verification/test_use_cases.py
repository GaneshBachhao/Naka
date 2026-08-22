# backend/tests/verification/test_use_cases.py
from __future__ import annotations

import datetime as dt
import uuid

from naka.shared.domain.ids import BusinessId
from naka.verification.application.dtos import RecordVerificationRequest
from naka.verification.application.ports import ReverificationSignals
from naka.verification.application.use_cases import BuildReverificationQueue, RecordVerification
from naka.verification.domain.entities import VerificationTier
from naka.verification.domain.events import BusinessVerified
from tests.verification.factories import make_record
from tests.verification.fakes import (
    FakeOutbox,
    FakeReverificationSignalsPort,
    FakeVerificationRecordRepository,
    FixedClock,
)

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


class TestRecordVerification:
    async def test_persists_record_and_enqueues_event(self) -> None:
        repo = FakeVerificationRecordRepository()
        outbox = FakeOutbox()
        use_case = RecordVerification(repo, outbox, FixedClock(_NOW))

        dto = await use_case.execute(
            RecordVerificationRequest(
                business_id=uuid.uuid4(),
                tier="field_verified",
                method="field_visit",
                verified_by="Agent Ramesh",
            )
        )

        assert len(repo.records) == 1
        assert dto.tier == "field_verified"
        assert len(outbox.enqueued) == 1
        assert isinstance(outbox.enqueued[0], BusinessVerified)


class TestBuildReverificationQueue:
    async def test_only_stale_records_returned(self) -> None:
        stale = make_record(
            tier=VerificationTier.SOURCED, verified_at=_NOW - dt.timedelta(days=100)
        )
        fresh = make_record(tier=VerificationTier.SOURCED, verified_at=_NOW - dt.timedelta(days=1))
        repo = FakeVerificationRecordRepository([stale, fresh])
        use_case = BuildReverificationQueue(repo, FakeReverificationSignalsPort(), FixedClock(_NOW))

        queue = await use_case.execute()

        assert len(queue) == 1
        assert queue[0].business_id == stale.business_id.value

    async def test_paying_business_ranked_first(self) -> None:
        business_a = BusinessId.new()
        business_b = BusinessId.new()
        record_a = make_record(
            business_id=business_a,
            tier=VerificationTier.SOURCED,
            verified_at=_NOW - dt.timedelta(days=100),
        )
        record_b = make_record(
            business_id=business_b,
            tier=VerificationTier.SOURCED,
            verified_at=_NOW - dt.timedelta(days=100),
        )
        repo = FakeVerificationRecordRepository([record_a, record_b])
        signals = FakeReverificationSignalsPort(
            {business_b: ReverificationSignals(is_paying=True, is_routable_category=False)}
        )
        use_case = BuildReverificationQueue(repo, signals, FixedClock(_NOW))

        queue = await use_case.execute()

        assert queue[0].business_id == business_b.value
        assert queue[0].is_paying is True
        assert queue[1].business_id == business_a.value
        assert queue[1].is_paying is False

    async def test_missing_signals_default_to_not_paying_not_routable(self) -> None:
        record = make_record(
            tier=VerificationTier.SOURCED, verified_at=_NOW - dt.timedelta(days=100)
        )
        repo = FakeVerificationRecordRepository([record])
        use_case = BuildReverificationQueue(repo, FakeReverificationSignalsPort(), FixedClock(_NOW))

        queue = await use_case.execute()

        assert queue[0].is_paying is False
        assert queue[0].is_routable_category is False
