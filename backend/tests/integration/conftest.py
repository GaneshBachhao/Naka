# backend/tests/integration/conftest.py
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from naka.shared.infrastructure.database import create_engine
from naka.shared.infrastructure.settings import Settings


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    # Each test runs inside one connection-level transaction that's rolled
    # back at the end, regardless of what the repositories under test do -
    # tests stay isolated from each other without truncating tables by hand.
    engine = create_engine(Settings().database_url)
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()
