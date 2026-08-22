# backend/src/naka/verification/application/ports.py
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from naka.shared.domain.ids import BusinessId
from naka.verification.domain.entities import VerificationRecord


class VerificationRecordRepository(Protocol):
    async def add(self, record: VerificationRecord) -> None: ...

    async def list_latest_per_business(self) -> list[VerificationRecord]: ...


@dataclass(frozen=True)
class ReverificationSignals:
    is_paying: bool
    is_routable_category: bool


class ReverificationSignalsPort(Protocol):
    """Hides the cross-context facts BuildReverificationQueue needs but
    verification doesn't own - whether a business pays (no billing context
    exists yet) and whether it sits in a routable category (catalog's
    Category.routable). Verification's application layer only knows this
    port's shape; whatever assembles the answer lives in Infrastructure."""

    async def get_signals(
        self, business_ids: Sequence[BusinessId]
    ) -> dict[BusinessId, ReverificationSignals]: ...
