# backend/src/naka/verification/domain/services.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from naka.shared.domain.ids import BusinessId
from naka.verification.domain.entities import VerificationRecord


@dataclass(frozen=True)
class ReverificationCandidate:
    """One business awaiting re-verification, with the external facts the
    queue ordering needs but VerificationRecord can't know on its own —
    a record only references its business by ID, never by object."""

    business_id: BusinessId
    record: VerificationRecord
    is_paying: bool
    is_routable_category: bool


def build_reverification_queue(
    candidates: Iterable[ReverificationCandidate], *, now: datetime
) -> list[ReverificationCandidate]:
    stale = [c for c in candidates if c.record.status_at(now).is_stale]
    return sorted(
        stale,
        key=lambda c: (not c.is_paying, not c.is_routable_category, c.record.verified_at),
    )
