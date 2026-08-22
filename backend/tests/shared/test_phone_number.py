# backend/tests/shared/test_phone_number.py
from __future__ import annotations

import pytest

from naka.shared.domain.phone_number import PhoneNumber


@pytest.mark.parametrize(
    "raw",
    [
        "9876543210",
        "+919876543210",
        "919876543210",
        "09876543210",
        "+91 98765 43210",
        "98765-43210",
    ],
)
def test_valid_indian_mobile_formats_normalize_to_ten_digits(raw: str) -> None:
    assert PhoneNumber(raw).value == "9876543210"


def test_e164_property() -> None:
    assert PhoneNumber("9876543210").e164 == "+919876543210"


def test_str_returns_e164() -> None:
    assert str(PhoneNumber("9876543210")) == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    [
        "12345",  # too short
        "5876543210",  # doesn't start with 6-9
        "98765432100",  # too long
        "abcdefghij",
        "",
    ],
)
def test_invalid_numbers_raise(raw: str) -> None:
    with pytest.raises(ValueError):
        PhoneNumber(raw)
