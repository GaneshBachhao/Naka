# backend/src/naka/worker.py
from __future__ import annotations

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from naka.enquiry.application.use_cases import ExpireEnquiryWindow
from naka.enquiry.infrastructure.repositories import SqlAlchemyEnquiryRepository
from naka.shared.infrastructure.clock import SystemClock
from naka.shared.infrastructure.database import create_engine, create_session_factory
from naka.shared.infrastructure.messaging import ManualMessagingAdapter
from naka.shared.infrastructure.outbox import SqlAlchemyOutbox
from naka.shared.infrastructure.settings import Settings
from naka.verification.application.use_cases import BuildReverificationQueue
from naka.verification.infrastructure.repositories import SqlAlchemyVerificationRecordRepository
from naka.verification.infrastructure.reverification_signals import SqlReverificationSignalsPort

logger = logging.getLogger(__name__)


async def expire_enquiry_windows(ctx: dict[str, Any]) -> int:
    clock = SystemClock()
    async with ctx["session_factory"]() as session:
        use_case = ExpireEnquiryWindow(
            SqlAlchemyEnquiryRepository(session),
            ManualMessagingAdapter(session, clock),
            SqlAlchemyOutbox(session),
            clock,
        )
        expired = await use_case.execute()
        await session.commit()
    if expired:
        logger.info("expired %d enquiry window(s)", len(expired))
    return len(expired)


async def decay_verifications(ctx: dict[str, Any]) -> int:
    # Only builds and logs the queue for now - nothing sends the actual
    # re-verification ping yet, since that use case doesn't exist (T4/T5
    # deliberately didn't invent one; see BuildReverificationQueue's own
    # scope notes). T8's ops console reverification-queue view is the
    # planned first real consumer of this data.
    clock = SystemClock()
    async with ctx["session_factory"]() as session:
        use_case = BuildReverificationQueue(
            SqlAlchemyVerificationRecordRepository(session),
            SqlReverificationSignalsPort(session),
            clock,
        )
        queue = await use_case.execute()
        await session.commit()
    if queue:
        logger.info("re-verification queue has %d business(es) due", len(queue))
    return len(queue)


async def _on_startup(ctx: dict[str, Any]) -> None:
    engine = create_engine(Settings().database_url)
    ctx["engine"] = engine
    ctx["session_factory"] = create_session_factory(engine)


async def _on_shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


class WorkerSettings:
    functions = [expire_enquiry_windows, decay_verifications]
    cron_jobs = [
        cron(expire_enquiry_windows),  # every minute (default cron granularity)
        cron(decay_verifications, hour=3, minute=0),  # once daily, off-peak
    ]
    on_startup = _on_startup
    on_shutdown = _on_shutdown
    redis_settings = RedisSettings.from_dsn(Settings().redis_url)
