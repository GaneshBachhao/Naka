# backend/tests/verification/test_entities.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.verification.domain.entities import VerificationTier
from tests.verification.factories import make_record


class TestVerificationRecordConstruction:
    def test_naive_verified_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_record(verified_at=dt.datetime(2026, 1, 1))  # no tzinfo

    def test_empty_verified_by_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_record(verified_by="  ")


class TestStatusAt:
    def test_naive_now_rejected(self) -> None:
        record = make_record(verified_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
        with pytest.raises(ValueError):
            record.status_at(dt.datetime(2026, 1, 2))  # no tzinfo

    @pytest.mark.parametrize(
        "tier,decay_days",
        [
            (VerificationTier.FIELD_VERIFIED, 180),
            (VerificationTier.OWNER_CONFIRMED, 120),
            (VerificationTier.CONTACT_VERIFIED, 90),
            (VerificationTier.SOURCED, 45),
        ],
    )
    def test_not_stale_one_second_before_decay_boundary(
        self, tier: VerificationTier, decay_days: int
    ) -> None:
        verified_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
        record = make_record(tier=tier, verified_at=verified_at)
        boundary = verified_at + dt.timedelta(days=decay_days)

        status = record.status_at(boundary - dt.timedelta(seconds=1))
        assert status.is_stale is False
        assert status.tier is tier

    @pytest.mark.parametrize(
        "tier,decay_days",
        [
            (VerificationTier.FIELD_VERIFIED, 180),
            (VerificationTier.OWNER_CONFIRMED, 120),
            (VerificationTier.CONTACT_VERIFIED, 90),
            (VerificationTier.SOURCED, 45),
        ],
    )
    def test_stale_exactly_at_decay_boundary(self, tier: VerificationTier, decay_days: int) -> None:
        verified_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
        record = make_record(tier=tier, verified_at=verified_at)
        boundary = verified_at + dt.timedelta(days=decay_days)

        status = record.status_at(boundary)
        assert status.is_stale is True

    @pytest.mark.parametrize(
        "tier,decay_days",
        [
            (VerificationTier.FIELD_VERIFIED, 180),
            (VerificationTier.OWNER_CONFIRMED, 120),
            (VerificationTier.CONTACT_VERIFIED, 90),
            (VerificationTier.SOURCED, 45),
        ],
    )
    def test_stale_one_second_after_decay_boundary(
        self, tier: VerificationTier, decay_days: int
    ) -> None:
        verified_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
        record = make_record(tier=tier, verified_at=verified_at)
        boundary = verified_at + dt.timedelta(days=decay_days)

        status = record.status_at(boundary + dt.timedelta(seconds=1))
        assert status.is_stale is True

    def test_days_until_decay_counts_down(self) -> None:
        verified_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
        record = make_record(tier=VerificationTier.SOURCED, verified_at=verified_at)

        status = record.status_at(verified_at + dt.timedelta(days=10))
        assert status.days_until_decay == 35  # 45-day window, 10 days elapsed

    def test_days_until_decay_is_negative_once_stale(self) -> None:
        verified_at = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
        record = make_record(tier=VerificationTier.SOURCED, verified_at=verified_at)

        status = record.status_at(verified_at + dt.timedelta(days=50))
        assert status.days_until_decay == -5
        assert status.is_stale is True
