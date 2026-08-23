# backend/tests/integration/test_worker.py
from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from naka.enquiry.infrastructure.models import EnquiryModel
from naka.enquiry.infrastructure.repositories import SqlAlchemyEnquiryRepository
from naka.shared.infrastructure.messaging import OperatorQueueMessageModel
from naka.shared.infrastructure.outbox import OutboxEventModel
from naka.verification.infrastructure.models import VerificationRecordModel
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository
from naka.worker import _on_shutdown, _on_startup, decay_verifications, expire_enquiry_windows
from tests.enquiry.factories import make_routed_enquiry
from tests.verification.factories import make_record

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def worker_ctx() -> AsyncIterator[dict[str, Any]]:
    # Unlike db_session, this binds a real session_factory that the job
    # functions under test will actually commit through, via the same
    # _on_startup/_on_shutdown WorkerSettings itself uses - proving the
    # composition root (repos + adapters + use case, wired exactly as
    # WorkerSettings wires them) runs end to end, not just that it
    # type-checks. Tests here clean up whatever they commit, since this
    # fixture has no rollback safety net.
    ctx: dict[str, Any] = {}
    await _on_startup(ctx)
    try:
        yield ctx
    finally:
        await _on_shutdown(ctx)


class TestWorkerJobs:
    async def test_expire_enquiry_windows_on_an_empty_schema(
        self, worker_ctx: dict[str, Any]
    ) -> None:
        assert await expire_enquiry_windows(worker_ctx) == 0

    async def test_decay_verifications_on_an_empty_schema(self, worker_ctx: dict[str, Any]) -> None:
        assert await decay_verifications(worker_ctx) == 0

    async def test_expire_enquiry_windows_finds_and_expires_a_due_enquiry(
        self, worker_ctx: dict[str, Any]
    ) -> None:
        # make_routed_enquiry()'s RoutedRequests are sent at the factory's
        # fixed NOW constant (2026-06-01) with a 30-minute reply window -
        # long expired relative to the real clock expire_enquiry_windows
        # actually uses, which is exactly what makes this enquiry "due".
        enquiry = make_routed_enquiry()
        async with worker_ctx["session_factory"]() as session:
            await SqlAlchemyEnquiryRepository(session).add(enquiry)
            await session.commit()

        # Snapshot rather than filter-by-content: ExpireEnquiryWindow's
        # outbox payload nests enquiry_id as {"value": "<uuid>"} (asdict()
        # recurses into EntityId's own field - see outbox.py), so matching
        # on it is fragile. Deleting "whatever's new since this snapshot" in
        # these two tables is robust regardless of payload shape.
        async with worker_ctx["session_factory"]() as session:
            existing_messages = set(
                (await session.execute(select(OperatorQueueMessageModel.id))).scalars().all()
            )
            existing_outbox_events = set(
                (await session.execute(select(OutboxEventModel.id))).scalars().all()
            )

        try:
            count = await expire_enquiry_windows(worker_ctx)
            assert count == 1
        finally:
            # ExpireEnquiryWindow also commits a customer notification (via
            # ManualMessagingAdapter) and an EnquiryUnanswered outbox row as
            # real side effects of this real run - not just the Enquiry
            # itself. This fixture has no rollback net, so all three must be
            # cleaned up or they leak into every later test run.
            async with worker_ctx["session_factory"]() as session:
                await session.execute(
                    delete(EnquiryModel).where(EnquiryModel.id == enquiry.id.value)
                )
                await session.execute(
                    delete(OperatorQueueMessageModel).where(
                        OperatorQueueMessageModel.id.not_in(existing_messages)
                    )
                )
                await session.execute(
                    delete(OutboxEventModel).where(
                        OutboxEventModel.id.not_in(existing_outbox_events)
                    )
                )
                await session.commit()

    async def test_decay_verifications_finds_a_stale_record(
        self, worker_ctx: dict[str, Any]
    ) -> None:
        record = make_record(
            verified_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=400)  # well past every tier
        )
        async with worker_ctx["session_factory"]() as session:
            await SqlAlchemyVerificationRecordRepository(session).add(record)
            await session.commit()

        try:
            count = await decay_verifications(worker_ctx)
            assert count == 1
        finally:
            async with worker_ctx["session_factory"]() as session:
                await session.execute(
                    delete(VerificationRecordModel).where(
                        VerificationRecordModel.id == record.id.value
                    )
                )
                await session.commit()
