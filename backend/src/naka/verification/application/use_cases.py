# backend/src/naka/verification/application/use_cases.py
from __future__ import annotations

from naka.shared.application.ports import Clock, OutboxPort
from naka.shared.domain.ids import BusinessId, VerificationId
from naka.verification.application.dtos import (
    RecordVerificationRequest,
    ReverificationQueueItemDTO,
    VerificationRecordDTO,
)
from naka.verification.application.ports import (
    ReverificationSignalsPort,
    VerificationRecordRepository,
)
from naka.verification.domain.entities import (
    VerificationMethod,
    VerificationRecord,
    VerificationTier,
)
from naka.verification.domain.events import BusinessVerified
from naka.verification.domain.services import ReverificationCandidate, build_reverification_queue


def _to_dto(record: VerificationRecord) -> VerificationRecordDTO:
    return VerificationRecordDTO(
        id=record.id.value,
        business_id=record.business_id.value,
        tier=record.tier.value,
        method=record.method.value,
        verified_by=record.verified_by,
        notes=record.notes,
    )


class RecordVerification:
    def __init__(
        self, records: VerificationRecordRepository, outbox: OutboxPort, clock: Clock
    ) -> None:
        self._records = records
        self._outbox = outbox
        self._clock = clock

    async def execute(self, request: RecordVerificationRequest) -> VerificationRecordDTO:
        record = VerificationRecord(
            id=VerificationId.new(),
            business_id=BusinessId(request.business_id),
            tier=VerificationTier(request.tier),
            method=VerificationMethod(request.method),
            verified_at=self._clock.now(),
            verified_by=request.verified_by,
            notes=request.notes,
        )
        await self._records.add(record)
        event = BusinessVerified(
            occurred_at=self._clock.now(),
            business_id=record.business_id,
            verification_id=record.id,
            tier=record.tier,
        )
        await self._outbox.enqueue((event,))
        return _to_dto(record)


class BuildReverificationQueue:
    def __init__(
        self,
        records: VerificationRecordRepository,
        signals: ReverificationSignalsPort,
        clock: Clock,
    ) -> None:
        self._records = records
        self._signals = signals
        self._clock = clock

    async def execute(self) -> list[ReverificationQueueItemDTO]:
        latest = await self._records.list_latest_per_business()
        business_ids = [record.business_id for record in latest]
        signals_by_business = await self._signals.get_signals(business_ids)

        candidates = [
            ReverificationCandidate(
                business_id=record.business_id,
                record=record,
                is_paying=signals_by_business[record.business_id].is_paying,
                is_routable_category=signals_by_business[record.business_id].is_routable_category,
            )
            for record in latest
        ]

        now = self._clock.now()
        queue = build_reverification_queue(candidates, now=now)
        return [
            ReverificationQueueItemDTO(
                business_id=candidate.business_id.value,
                tier=candidate.record.tier.value,
                days_until_decay=candidate.record.status_at(now).days_until_decay,
                is_paying=candidate.is_paying,
                is_routable_category=candidate.is_routable_category,
            )
            for candidate in queue
        ]
