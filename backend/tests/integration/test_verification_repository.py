# backend/tests/integration/test_verification_repository.py
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.domain.ids import BusinessId
from naka.verification.domain.entities import VerificationTier
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository
from tests.verification.factories import make_record

pytestmark = pytest.mark.integration


class TestSqlAlchemyVerificationRecordRepository:
    async def test_round_trips_a_record(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVerificationRecordRepository(db_session)
        record = make_record()

        await repo.add(record)
        await db_session.flush()
        db_session.expunge_all()

        [loaded] = await repo.list_latest_per_business()
        assert loaded == record

    async def test_returns_only_the_latest_record_per_business(
        self, db_session: AsyncSession
    ) -> None:
        business_id = BusinessId.new()
        older = make_record(
            business_id=business_id,
            tier=VerificationTier.SOURCED,
            verified_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        )
        newer = make_record(
            business_id=business_id,
            tier=VerificationTier.FIELD_VERIFIED,
            verified_at=dt.datetime(2026, 3, 1, tzinfo=dt.UTC),
        )
        repo = SqlAlchemyVerificationRecordRepository(db_session)
        await repo.add(older)
        await repo.add(newer)
        await db_session.flush()
        db_session.expunge_all()

        [loaded] = await repo.list_latest_per_business()
        assert loaded.tier is VerificationTier.FIELD_VERIFIED
        assert loaded.verified_at == newer.verified_at

    async def test_returns_one_row_per_distinct_business(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyVerificationRecordRepository(db_session)
        await repo.add(make_record(business_id=BusinessId.new()))
        await repo.add(make_record(business_id=BusinessId.new()))
        await db_session.flush()
        db_session.expunge_all()

        results = await repo.list_latest_per_business()
        assert len(results) == 2
