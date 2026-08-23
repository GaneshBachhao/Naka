# backend/src/naka/enquiry/api/router.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from naka.enquiry.api.deps import (
    get_enquiry_queue_use_case,
    get_list_operator_queue_use_case,
    get_mark_operator_message_sent_use_case,
    get_parse_and_route_enquiry_use_case,
    get_record_business_response_use_case,
    get_routed_request_by_token_use_case,
    get_submit_enquiry_use_case,
)
from naka.enquiry.api.schemas import OperatorQueueMessageSchema, RecordResponseBody
from naka.enquiry.application.dtos import (
    EnquiryDTO,
    EnquiryQueueItemDTO,
    RecordBusinessResponseRequest,
    RecordBusinessResponseResult,
    RoutedRequestPageDTO,
    SubmitEnquiryRequest,
)
from naka.enquiry.application.errors import EnquiryNotFoundError, InsufficientRoutingCandidatesError
from naka.enquiry.application.use_cases import (
    GetRoutedRequestByToken,
    ListEnquiryQueue,
    ParseAndRouteEnquiry,
    RecordBusinessResponse,
    SubmitEnquiry,
)
from naka.shared.api.deps import require_ops_auth
from naka.shared.api.rate_limit import rate_limit
from naka.shared.application.use_cases import ListOperatorQueue, MarkOperatorMessageSent
from naka.shared.domain.ids import EnquiryId

_submit_rate_limit = rate_limit(limit=10, window_seconds=60)
_response_page_rate_limit = rate_limit(limit=30, window_seconds=60)
_record_response_rate_limit = rate_limit(limit=10, window_seconds=60)

public_router = APIRouter(tags=["enquiries"])
ops_router = APIRouter(
    prefix="/ops", tags=["ops: enquiries"], dependencies=[Depends(require_ops_auth)]
)


@public_router.post(
    "/api/enquiries",
    response_model=EnquiryDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a customer enquiry",
    dependencies=[Depends(_submit_rate_limit)],
)
async def submit_enquiry(
    request: SubmitEnquiryRequest,
    use_case: SubmitEnquiry = Depends(get_submit_enquiry_use_case),
) -> EnquiryDTO:
    return await use_case.execute(request)


@public_router.get(
    "/r/{token}",
    response_model=RoutedRequestPageDTO,
    summary="Business response page data",
    dependencies=[Depends(_response_page_rate_limit)],
)
async def get_response_page(
    token: str,
    use_case: GetRoutedRequestByToken = Depends(get_routed_request_by_token_use_case),
) -> RoutedRequestPageDTO:
    return await use_case.execute(token)


@public_router.post(
    "/r/{token}",
    response_model=RecordBusinessResponseResult,
    summary="Record a business's single-use response",
    dependencies=[Depends(_record_response_rate_limit)],
)
async def record_response(
    token: str,
    body: RecordResponseBody,
    use_case: RecordBusinessResponse = Depends(get_record_business_response_use_case),
) -> RecordBusinessResponseResult:
    request = RecordBusinessResponseRequest(token=token, **body.model_dump())
    return await use_case.execute(request)


@ops_router.get(
    "/enquiries",
    response_model=list[EnquiryQueueItemDTO],
    summary="Live enquiry queue with age and status",
)
async def list_enquiry_queue(
    use_case: ListEnquiryQueue = Depends(get_enquiry_queue_use_case),
) -> list[EnquiryQueueItemDTO]:
    return await use_case.execute()


@ops_router.post(
    "/enquiries/{enquiry_id}/route",
    response_model=EnquiryDTO,
    summary="Parse an enquiry's intent and route it to eligible businesses",
)
async def route_enquiry(
    enquiry_id: uuid.UUID,
    use_case: ParseAndRouteEnquiry = Depends(get_parse_and_route_enquiry_use_case),
) -> EnquiryDTO:
    try:
        return await use_case.execute(EnquiryId(enquiry_id))
    except EnquiryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enquiry not found") from exc
    except InsufficientRoutingCandidatesError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Not enough eligible businesses to route to"
        ) from exc


@ops_router.get(
    "/operator-queue",
    response_model=list[OperatorQueueMessageSchema],
    summary="Pending Wizard-of-Oz messages waiting to be sent by hand",
)
async def list_operator_queue(
    use_case: ListOperatorQueue = Depends(get_list_operator_queue_use_case),
) -> list[OperatorQueueMessageSchema]:
    messages = await use_case.execute()
    return [OperatorQueueMessageSchema(**vars(message)) for message in messages]


@ops_router.post(
    "/operator-queue/{message_id}/mark-sent",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a queued message as sent, once the operator has actually sent it",
)
async def mark_operator_message_sent(
    message_id: uuid.UUID,
    use_case: MarkOperatorMessageSent = Depends(get_mark_operator_message_sent_use_case),
) -> None:
    await use_case.execute(message_id)
