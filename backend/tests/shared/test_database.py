# backend/tests/shared/test_database.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from naka.shared.infrastructure.database import create_engine, create_session_factory


async def test_create_session_factory_builds_a_working_sessionmaker() -> None:
    engine = create_engine("postgresql+asyncpg://naka:naka@localhost:5432/naka")
    try:
        factory = create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)
        session = factory()
        try:
            assert isinstance(session, AsyncSession)
            assert session.sync_session.autoflush is True
        finally:
            await session.close()
    finally:
        await engine.dispose()
