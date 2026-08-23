# backend/src/naka/verification/api/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from naka.shared.api.deps import require_ops_auth
from naka.verification.api.deps import (
    get_build_reverification_queue_use_case,
    get_record_verification_use_case,
)
from naka.verification.application.dtos import (
    RecordVerificationRequest,
    ReverificationQueueItemDTO,
    VerificationRecordDTO,
)
from naka.verification.application.use_cases import BuildReverificationQueue, RecordVerification

ops_router = APIRouter(
    prefix="/ops", tags=["ops: verification"], dependencies=[Depends(require_ops_auth)]
)


@ops_router.post(
    "/verifications",
    response_model=VerificationRecordDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Record a business verification",
)
async def record_verification(
    request: RecordVerificationRequest,
    use_case: RecordVerification = Depends(get_record_verification_use_case),
) -> VerificationRecordDTO:
    return await use_case.execute(request)


@ops_router.get(
    "/reverification-queue",
    response_model=list[ReverificationQueueItemDTO],
    summary="Businesses due for re-verification, ranked by priority",
)
async def get_reverification_queue(
    use_case: BuildReverificationQueue = Depends(get_build_reverification_queue_use_case),
) -> list[ReverificationQueueItemDTO]:
    return await use_case.execute()
