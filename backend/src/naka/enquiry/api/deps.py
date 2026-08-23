# backend/src/naka/enquiry/api/deps.py
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.infrastructure.repositories import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyLocalityRepository,
)
from naka.enquiry.application.use_cases import (
    GetRoutedRequestByToken,
    ListEnquiryQueue,
    ParseAndRouteEnquiry,
    RecordBusinessResponse,
    SubmitEnquiry,
)
from naka.enquiry.infrastructure.ai_adapter import AnthropicAIAdapter
from naka.enquiry.infrastructure.locality_lookup import SqlLocalityNameLookup
from naka.enquiry.infrastructure.repositories import SqlAlchemyEnquiryRepository
from naka.enquiry.infrastructure.routing_lookup import SqlRoutingCandidateLookupPort
from naka.shared.api.deps import get_clock, get_session, get_settings
from naka.shared.application.use_cases import ListOperatorQueue, MarkOperatorMessageSent
from naka.shared.infrastructure.clock import SystemClock
from naka.shared.infrastructure.messaging import ManualMessagingAdapter, SqlAlchemyOperatorQueue
from naka.shared.infrastructure.outbox import SqlAlchemyOutbox
from naka.shared.infrastructure.settings import Settings


def get_enquiry_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyEnquiryRepository:
    return SqlAlchemyEnquiryRepository(session)


def get_messaging(
    session: AsyncSession = Depends(get_session), clock: SystemClock = Depends(get_clock)
) -> ManualMessagingAdapter:
    return ManualMessagingAdapter(session, clock)


def get_outbox(session: AsyncSession = Depends(get_session)) -> SqlAlchemyOutbox:
    return SqlAlchemyOutbox(session)


def get_ai_client(
    request: Request, session: AsyncSession = Depends(get_session)
) -> AnthropicAIAdapter:
    return AnthropicAIAdapter(
        request.app.state.anthropic_client,
        SqlAlchemyCategoryRepository(session),
        SqlAlchemyLocalityRepository(session),
    )


def get_routing_candidates(
    session: AsyncSession = Depends(get_session), clock: SystemClock = Depends(get_clock)
) -> SqlRoutingCandidateLookupPort:
    return SqlRoutingCandidateLookupPort(session, clock)


def get_locality_name_lookup(
    session: AsyncSession = Depends(get_session),
) -> SqlLocalityNameLookup:
    return SqlLocalityNameLookup(session)


def get_submit_enquiry_use_case(
    enquiries: SqlAlchemyEnquiryRepository = Depends(get_enquiry_repository),
    outbox: SqlAlchemyOutbox = Depends(get_outbox),
    clock: SystemClock = Depends(get_clock),
) -> SubmitEnquiry:
    return SubmitEnquiry(enquiries, outbox, clock)


def get_parse_and_route_enquiry_use_case(
    enquiries: SqlAlchemyEnquiryRepository = Depends(get_enquiry_repository),
    ai_client: AnthropicAIAdapter = Depends(get_ai_client),
    candidates: SqlRoutingCandidateLookupPort = Depends(get_routing_candidates),
    messaging: ManualMessagingAdapter = Depends(get_messaging),
    outbox: SqlAlchemyOutbox = Depends(get_outbox),
    clock: SystemClock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> ParseAndRouteEnquiry:
    return ParseAndRouteEnquiry(
        enquiries,
        ai_client,
        candidates,
        messaging,
        outbox,
        clock,
        settings.response_link_base_url,
    )


def get_record_business_response_use_case(
    enquiries: SqlAlchemyEnquiryRepository = Depends(get_enquiry_repository),
    messaging: ManualMessagingAdapter = Depends(get_messaging),
    outbox: SqlAlchemyOutbox = Depends(get_outbox),
    clock: SystemClock = Depends(get_clock),
) -> RecordBusinessResponse:
    return RecordBusinessResponse(enquiries, messaging, outbox, clock)


def get_routed_request_by_token_use_case(
    enquiries: SqlAlchemyEnquiryRepository = Depends(get_enquiry_repository),
    localities: SqlLocalityNameLookup = Depends(get_locality_name_lookup),
    clock: SystemClock = Depends(get_clock),
) -> GetRoutedRequestByToken:
    return GetRoutedRequestByToken(enquiries, localities, clock)


def get_enquiry_queue_use_case(
    enquiries: SqlAlchemyEnquiryRepository = Depends(get_enquiry_repository),
    clock: SystemClock = Depends(get_clock),
) -> ListEnquiryQueue:
    return ListEnquiryQueue(enquiries, clock)


def get_operator_queue(session: AsyncSession = Depends(get_session)) -> SqlAlchemyOperatorQueue:
    return SqlAlchemyOperatorQueue(session)


def get_list_operator_queue_use_case(
    queue: SqlAlchemyOperatorQueue = Depends(get_operator_queue),
) -> ListOperatorQueue:
    return ListOperatorQueue(queue)


def get_mark_operator_message_sent_use_case(
    queue: SqlAlchemyOperatorQueue = Depends(get_operator_queue),
    clock: SystemClock = Depends(get_clock),
) -> MarkOperatorMessageSent:
    return MarkOperatorMessageSent(queue, clock)
