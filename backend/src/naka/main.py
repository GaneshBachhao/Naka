# backend/src/naka/main.py
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from naka.catalog.api.router import ops_catalog_router
from naka.catalog.api.router import ops_router as catalog_ops_router
from naka.catalog.api.router import public_router as catalog_public_router
from naka.enquiry.api.router import ops_router as enquiry_ops_router
from naka.enquiry.api.router import public_router as enquiry_public_router
from naka.shared.infrastructure.database import create_engine, create_session_factory
from naka.shared.infrastructure.settings import Settings
from naka.verification.api.router import ops_router as verification_ops_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    engine = create_engine(settings.database_url)
    redis = Redis.from_url(settings.redis_url)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.redis = redis
    app.state.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        yield
    finally:
        await engine.dispose()
        await redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Naka", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings().cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(enquiry_public_router)
    app.include_router(enquiry_ops_router)
    app.include_router(catalog_public_router)
    app.include_router(catalog_ops_router)
    app.include_router(ops_catalog_router)
    app.include_router(verification_ops_router)

    return app


app = create_app()
