# backend/src/naka/verification/api/deps.py
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.api.deps import get_clock, get_session
from naka.shared.infrastructure.clock import SystemClock
from naka.shared.infrastructure.outbox import SqlAlchemyOutbox
from naka.verification.application.use_cases import BuildReverificationQueue, RecordVerification
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository
from naka.verification.infrastructure.reverification_signals import SqlReverificationSignalsPort


def get_verification_record_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyVerificationRecordRepository:
    return SqlAlchemyVerificationRecordRepository(session)


def get_reverification_signals(
    session: AsyncSession = Depends(get_session),
) -> SqlReverificationSignalsPort:
    return SqlReverificationSignalsPort(session)


def get_record_verification_use_case(
    records: SqlAlchemyVerificationRecordRepository = Depends(get_verification_record_repository),
    session: AsyncSession = Depends(get_session),
    clock: SystemClock = Depends(get_clock),
) -> RecordVerification:
    return RecordVerification(records, SqlAlchemyOutbox(session), clock)


def get_build_reverification_queue_use_case(
    records: SqlAlchemyVerificationRecordRepository = Depends(get_verification_record_repository),
    signals: SqlReverificationSignalsPort = Depends(get_reverification_signals),
    clock: SystemClock = Depends(get_clock),
) -> BuildReverificationQueue:
    return BuildReverificationQueue(records, signals, clock)
