# backend/tests/shared/test_events.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.shared.domain.events import DomainEvent


def test_naive_occurred_at_rejected() -> None:
    with pytest.raises(ValueError):
        DomainEvent(occurred_at=dt.datetime(2026, 1, 1))


def test_aware_occurred_at_accepted() -> None:
    DomainEvent(occurred_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC))
