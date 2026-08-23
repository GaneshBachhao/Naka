# backend/tests/shared/test_outbox_serialization.py
from __future__ import annotations

import datetime as dt
import uuid

import pytest

from naka.shared.infrastructure.outbox import _json_default


def test_json_default_serializes_uuid() -> None:
    value = uuid.uuid4()
    assert _json_default(value) == str(value)


def test_json_default_serializes_datetime() -> None:
    value = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    assert _json_default(value) == value.isoformat()


def test_json_default_raises_for_unsupported_types() -> None:
    with pytest.raises(TypeError):
        _json_default(object())
