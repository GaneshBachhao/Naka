# backend/src/naka/verification/infrastructure/repositories.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naka.verification.domain.entities import VerificationRecord
from naka.verification.infrastructure.mappers import record_to_domain, record_to_model
from naka.verification.infrastructure.models import VerificationRecordModel


class SqlAlchemyVerificationRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: VerificationRecord) -> None:
        self._session.add(record_to_model(record))

    async def list_latest_per_business(self) -> list[VerificationRecord]:
        # DISTINCT ON is Postgres-specific, matching this repo's Postgres-only
        # stack - it picks the first row per business_id after ordering, which
        # is exactly "the latest verification record per business."
        stmt = (
            select(VerificationRecordModel)
            .distinct(VerificationRecordModel.business_id)
            .order_by(
                VerificationRecordModel.business_id,
                VerificationRecordModel.verified_at.desc(),
            )
        )
        result = await self._session.execute(stmt)
        return [record_to_domain(model) for model in result.scalars().all()]
