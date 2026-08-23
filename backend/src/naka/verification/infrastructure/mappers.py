# backend/src/naka/verification/infrastructure/mappers.py
from __future__ import annotations

from naka.shared.domain.ids import BusinessId, VerificationId
from naka.verification.domain.entities import (
    VerificationMethod,
    VerificationRecord,
    VerificationTier,
)
from naka.verification.infrastructure.models import VerificationRecordModel


def record_to_domain(model: VerificationRecordModel) -> VerificationRecord:
    return VerificationRecord(
        id=VerificationId(model.id),
        business_id=BusinessId(model.business_id),
        tier=VerificationTier(model.tier),
        method=VerificationMethod(model.method),
        verified_at=model.verified_at,
        verified_by=model.verified_by,
        notes=model.notes,
    )


def record_to_model(record: VerificationRecord) -> VerificationRecordModel:
    return VerificationRecordModel(
        id=record.id.value,
        business_id=record.business_id.value,
        tier=record.tier.value,
        method=record.method.value,
        verified_at=record.verified_at,
        verified_by=record.verified_by,
        notes=record.notes,
    )
