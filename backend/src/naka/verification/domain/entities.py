# backend/src/naka/verification/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from naka.shared.domain.ids import BusinessId, VerificationId


class VerificationTier(StrEnum):
    FIELD_VERIFIED = "field_verified"
    OWNER_CONFIRMED = "owner_confirmed"
    CONTACT_VERIFIED = "contact_verified"
    SOURCED = "sourced"

    @property
    def decay_window(self) -> timedelta:
        return _DECAY_WINDOWS[self]


_DECAY_WINDOWS: dict[VerificationTier, timedelta] = {
    VerificationTier.FIELD_VERIFIED: timedelta(days=180),
    VerificationTier.OWNER_CONFIRMED: timedelta(days=120),
    VerificationTier.CONTACT_VERIFIED: timedelta(days=90),
    VerificationTier.SOURCED: timedelta(days=45),
}


class VerificationMethod(StrEnum):
    FIELD_VISIT = "field_visit"
    OWNER_CONFIRMATION = "owner_confirmation"
    PHONE_CALL = "phone_call"
    PUBLIC_SOURCE = "public_source"


@dataclass(frozen=True)
class VerificationStatus:
    tier: VerificationTier
    is_stale: bool
    days_until_decay: int


@dataclass(frozen=True)
class VerificationRecord:
    id: VerificationId
    business_id: BusinessId
    tier: VerificationTier
    method: VerificationMethod
    verified_at: datetime
    verified_by: str
    notes: str = ""

    def __post_init__(self) -> None:
        if self.verified_at.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")
        if not self.verified_by.strip():
            raise ValueError("verified_by must not be empty")

    def status_at(self, now: datetime) -> VerificationStatus:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        decay_at = self.verified_at + self.tier.decay_window
        is_stale = now >= decay_at
        return VerificationStatus(
            tier=self.tier,
            is_stale=is_stale,
            days_until_decay=(decay_at - now).days,
        )
