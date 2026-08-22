# backend/tests/verification/test_services.py
from __future__ import annotations

import datetime as dt

from naka.shared.domain.ids import BusinessId
from naka.verification.domain.entities import VerificationTier
from naka.verification.domain.services import ReverificationCandidate, build_reverification_queue
from tests.verification.factories import make_record

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)
_STALE_SOURCED = _NOW - dt.timedelta(days=100)  # 45-day window: well expired
_FRESH_SOURCED = _NOW - dt.timedelta(days=1)  # not expired


def _candidate(
    *, is_paying: bool, is_routable_category: bool, verified_at: dt.datetime
) -> ReverificationCandidate:
    return ReverificationCandidate(
        business_id=BusinessId.new(),
        record=make_record(tier=VerificationTier.SOURCED, verified_at=verified_at),
        is_paying=is_paying,
        is_routable_category=is_routable_category,
    )


def test_only_stale_records_are_queued() -> None:
    stale = _candidate(is_paying=False, is_routable_category=False, verified_at=_STALE_SOURCED)
    fresh = _candidate(is_paying=False, is_routable_category=False, verified_at=_FRESH_SOURCED)

    queue = build_reverification_queue([stale, fresh], now=_NOW)

    assert queue == [stale]


def test_paying_businesses_come_before_non_paying() -> None:
    paying = _candidate(is_paying=True, is_routable_category=False, verified_at=_STALE_SOURCED)
    non_paying = _candidate(is_paying=False, is_routable_category=False, verified_at=_STALE_SOURCED)

    queue = build_reverification_queue([non_paying, paying], now=_NOW)

    assert queue == [paying, non_paying]


def test_routable_category_breaks_ties_among_equally_paying_businesses() -> None:
    routable = _candidate(is_paying=False, is_routable_category=True, verified_at=_STALE_SOURCED)
    not_routable = _candidate(
        is_paying=False, is_routable_category=False, verified_at=_STALE_SOURCED
    )

    queue = build_reverification_queue([not_routable, routable], now=_NOW)

    assert queue == [routable, not_routable]


def test_oldest_verification_breaks_ties_among_equal_paying_and_routable() -> None:
    older = _candidate(
        is_paying=True, is_routable_category=True, verified_at=_NOW - dt.timedelta(days=200)
    )
    newer = _candidate(
        is_paying=True, is_routable_category=True, verified_at=_NOW - dt.timedelta(days=100)
    )

    queue = build_reverification_queue([newer, older], now=_NOW)

    assert queue == [older, newer]


def test_full_ordering_precedence() -> None:
    # paying > routable > oldest, in that strict order
    paying_not_routable_old = _candidate(
        is_paying=True, is_routable_category=False, verified_at=_NOW - dt.timedelta(days=200)
    )
    paying_routable_new = _candidate(
        is_paying=True, is_routable_category=True, verified_at=_NOW - dt.timedelta(days=50)
    )
    non_paying_routable_oldest = _candidate(
        is_paying=False, is_routable_category=True, verified_at=_NOW - dt.timedelta(days=300)
    )

    queue = build_reverification_queue(
        [non_paying_routable_oldest, paying_not_routable_old, paying_routable_new], now=_NOW
    )

    assert queue == [paying_routable_new, paying_not_routable_old, non_paying_routable_oldest]
