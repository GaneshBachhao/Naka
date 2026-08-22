# backend/src/naka/verification/domain/events.py
from __future__ import annotations

from dataclasses import dataclass

from naka.shared.domain.events import DomainEvent
from naka.shared.domain.ids import BusinessId, VerificationId
from naka.verification.domain.entities import VerificationTier


@dataclass(frozen=True)
class BusinessVerified(DomainEvent):
    business_id: BusinessId
    verification_id: VerificationId
    tier: VerificationTier


@dataclass(frozen=True)
class VerificationExpired(DomainEvent):
    business_id: BusinessId
    verification_id: VerificationId
    tier: VerificationTier
