# backend/tests/verification/test_events.py
from __future__ import annotations

import datetime as dt

from naka.shared.domain.ids import BusinessId, VerificationId
from naka.verification.domain.entities import VerificationTier
from naka.verification.domain.events import BusinessVerified, VerificationExpired


def test_business_verified_carries_tier_and_ids() -> None:
    business_id = BusinessId.new()
    verification_id = VerificationId.new()

    event = BusinessVerified(
        occurred_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        business_id=business_id,
        verification_id=verification_id,
        tier=VerificationTier.FIELD_VERIFIED,
    )

    assert event.business_id == business_id
    assert event.verification_id == verification_id
    assert event.tier is VerificationTier.FIELD_VERIFIED


def test_verification_expired_carries_tier_and_ids() -> None:
    business_id = BusinessId.new()
    verification_id = VerificationId.new()

    event = VerificationExpired(
        occurred_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        business_id=business_id,
        verification_id=verification_id,
        tier=VerificationTier.SOURCED,
    )

    assert event.business_id == business_id
    assert event.verification_id == verification_id
    assert event.tier is VerificationTier.SOURCED
