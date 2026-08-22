# backend/tests/verification/factories.py
from __future__ import annotations

import dataclasses
import datetime as dt

from naka.shared.domain.ids import BusinessId, VerificationId
from naka.verification.domain.entities import (
    VerificationMethod,
    VerificationRecord,
    VerificationTier,
)


def make_record(**overrides: object) -> VerificationRecord:
    record = VerificationRecord(
        id=VerificationId.new(),
        business_id=BusinessId.new(),
        tier=VerificationTier.FIELD_VERIFIED,
        method=VerificationMethod.FIELD_VISIT,
        verified_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        verified_by="Agent Ramesh",
        notes="",
    )
    return dataclasses.replace(record, **overrides) if overrides else record
