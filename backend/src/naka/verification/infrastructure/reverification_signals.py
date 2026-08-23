# backend/src/naka/verification/infrastructure/reverification_signals.py
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from naka.shared.domain.ids import BusinessId
from naka.verification.application.ports import ReverificationSignals

_QUERY = text("""
    SELECT b.id AS business_id,
           EXISTS (
               SELECT 1 FROM catalog_categories c
               WHERE c.id = ANY(b.category_ids) AND c.routable = true
           ) AS is_routable_category
    FROM catalog_businesses b
    WHERE b.id = ANY(:business_ids)
""")


class SqlReverificationSignalsPort:
    """is_paying is always False - there's no billing context yet (T4 flagged
    this same gap for a hypothetical PaymentStatusPort). Every business is
    treated as non-paying until billing exists; the queue's ordering then
    degrades gracefully to routable-category-then-oldest, which is still a
    reasonable default rather than a broken one."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_signals(
        self, business_ids: Sequence[BusinessId]
    ) -> dict[BusinessId, ReverificationSignals]:
        if not business_ids:
            return {}

        rows = (
            await self._session.execute(
                _QUERY, {"business_ids": [business_id.value for business_id in business_ids]}
            )
        ).all()
        found = {
            BusinessId(row.business_id): ReverificationSignals(
                is_paying=False, is_routable_category=row.is_routable_category
            )
            for row in rows
        }
        return {
            business_id: found.get(
                business_id, ReverificationSignals(is_paying=False, is_routable_category=False)
            )
            for business_id in business_ids
        }
