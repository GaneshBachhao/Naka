# backend/src/naka/shared/domain/phone_number.py
from __future__ import annotations

import re
from dataclasses import dataclass

_INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def _normalize(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits


@dataclass(frozen=True)
class PhoneNumber:
    """A validated Indian mobile number, stored as bare 10 digits."""

    value: str

    def __post_init__(self) -> None:
        normalized = _normalize(self.value)
        if not _INDIAN_MOBILE.match(normalized):
            raise ValueError(f"Not a valid Indian mobile number: {self.value!r}")
        object.__setattr__(self, "value", normalized)

    @property
    def e164(self) -> str:
        return f"+91{self.value}"

    def __str__(self) -> str:
        return self.e164
