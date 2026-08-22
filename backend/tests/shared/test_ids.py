# backend/tests/shared/test_ids.py
from __future__ import annotations

import uuid

from naka.shared.domain.ids import BusinessId, RegionId


def test_new_generates_unique_ids() -> None:
    assert RegionId.new() != RegionId.new()


def test_equal_value_ids_of_same_type_are_equal() -> None:
    value = uuid.uuid4()
    assert RegionId(value) == RegionId(value)


def test_ids_of_different_types_are_never_equal_even_with_same_uuid() -> None:
    value = uuid.uuid4()
    assert RegionId(value) != BusinessId(value)


def test_str_returns_the_raw_uuid() -> None:
    value = uuid.uuid4()
    assert str(RegionId(value)) == str(value)
