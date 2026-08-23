# backend/tests/shared/test_clock.py
from __future__ import annotations

import datetime as dt

from naka.shared.infrastructure.clock import SystemClock


def test_now_is_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is dt.UTC


def test_now_is_close_to_real_time() -> None:
    before = dt.datetime.now(dt.UTC)
    now = SystemClock().now()
    after = dt.datetime.now(dt.UTC)
    assert before <= now <= after
