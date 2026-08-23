# backend/tests/integration/test_api.py
from __future__ import annotations

import uuid
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import DeclarativeBase

from naka.catalog.infrastructure.models import BusinessModel
from naka.enquiry.infrastructure.models import EnquiryModel
from naka.main import create_app
from naka.shared.api.security import create_access_token
from naka.shared.infrastructure.database import create_engine, create_session_factory
from naka.shared.infrastructure.outbox import OutboxEventModel
from naka.shared.infrastructure.settings import Settings
from naka.verification.infrastructure.models import VerificationRecordModel

pytestmark = pytest.mark.integration

# These don't override any dependency - unlike tests/api/*, which stub the
# use case and so never actually exercise api/deps.py's factory functions.
# The point here is the opposite: prove the real composition root
# (get_session -> repository -> use case -> router) works end to end
# against a real database, the same discipline T5 applied to the ARQ
# worker's wiring.
#
# Cleanup must NOT reuse app.state.engine/session_factory: TestClient runs
# the app's lifespan (and therefore that engine) inside its own internal
# event loop via a thread portal, distinct from this async test function's
# own pytest-asyncio loop. Touching that engine's connections from here
# raises "Future attached to a different loop" (asyncpg is loop-bound) and
# hangs. A completely independent engine, scoped to this test's own loop,
# sidesteps the problem entirely - and works whether it's used inside or
# outside the `with TestClient(...)` block, since the fix is which engine
# object is touched, not when.


def _ops_headers() -> dict[str, str]:
    settings = Settings()
    token = create_access_token("integration-test", settings.jwt_secret, settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


async def _delete(model: type[DeclarativeBase], row_id: uuid.UUID) -> None:
    engine = create_engine(Settings().database_url)
    try:
        async with create_session_factory(engine)() as session:
            await session.execute(delete(model).where(model.id == row_id))  # type: ignore[attr-defined]
            await session.commit()
    finally:
        await engine.dispose()


async def _outbox_snapshot() -> set[uuid.UUID]:
    engine = create_engine(Settings().database_url)
    try:
        async with create_session_factory(engine)() as session:
            result = await session.execute(select(OutboxEventModel.id))
            return set(result.scalars().all())
    finally:
        await engine.dispose()


async def _delete_new_outbox_events(existing: set[uuid.UUID]) -> None:
    # The use cases behind these two endpoints (SubmitEnquiry,
    # RecordVerification) also commit an outbox row as a real side effect -
    # not just the aggregate itself. Matching by content is fragile (see
    # outbox.py: dataclasses.asdict() nests EntityId fields as {"value":
    # "<uuid>"}), so this deletes whatever's new since the snapshot instead,
    # the same approach T5's worker integration tests use.
    engine = create_engine(Settings().database_url)
    try:
        async with create_session_factory(engine)() as session:
            await session.execute(
                delete(OutboxEventModel).where(OutboxEventModel.id.not_in(existing))
            )
            await session.commit()
    finally:
        await engine.dispose()


class TestCreateBusinessEndToEnd:
    async def test_creates_and_fetches_a_real_business(self) -> None:
        app = create_app()
        with TestClient(app) as client:
            body = {
                "region_id": str(uuid.uuid4()),
                "locality_id": str(uuid.uuid4()),
                "name_mr": "साई कृषी केंद्र",
                "name_en": "Sai Krushi Kendra",
                "owner_name": "Ramesh Patil",
                "category_ids": [str(uuid.uuid4())],
                "contact_numbers": ["9876543210"],
                "whatsapp_number": "9876543210",
                "landmark": "Bus stand road",
                "latitude": 21.15,
                "longitude": 74.33,
                "opening_hours": {
                    str(i): {
                        "open_time": time(9, 0).isoformat(),
                        "close_time": time(21, 0).isoformat(),
                    }
                    for i in range(7)
                },
                "attributes": [],
            }

            response = client.post("/ops/businesses", json=body, headers=_ops_headers())
            business_id = uuid.UUID(response.json()["id"])
            try:
                assert response.status_code == 201
                assert response.json()["name_en"] == "Sai Krushi Kendra"

                fetched = client.get(f"/ops/businesses/{business_id}", headers=_ops_headers())
                assert fetched.status_code == 200
                assert fetched.json()["name_en"] == "Sai Krushi Kendra"
            finally:
                await _delete(BusinessModel, business_id)


class TestSubmitEnquiryEndToEnd:
    async def test_creates_a_real_enquiry(self) -> None:
        existing_outbox_events = await _outbox_snapshot()
        app = create_app()
        with TestClient(app) as client:
            body = {
                "region_id": str(uuid.uuid4()),
                "raw_text": "कापसासाठी औषध कोणाकडे आहे?",
                "customer_phone": "9876543210",
            }

            response = client.post("/api/enquiries", json=body)
            enquiry_id = uuid.UUID(response.json()["id"])
            try:
                assert response.status_code == 201
                assert response.json()["status"] == "received"
            finally:
                await _delete(EnquiryModel, enquiry_id)
                await _delete_new_outbox_events(existing_outbox_events)


class TestRecordVerificationEndToEnd:
    async def test_creates_a_real_verification_record(self) -> None:
        existing_outbox_events = await _outbox_snapshot()
        app = create_app()
        with TestClient(app) as client:
            body = {
                "business_id": str(uuid.uuid4()),
                "tier": "field_verified",
                "method": "field_visit",
                "verified_by": "Agent Ramesh",
            }

            response = client.post("/ops/verifications", json=body, headers=_ops_headers())
            record_id = uuid.UUID(response.json()["id"])
            try:
                assert response.status_code == 201
                assert response.json()["tier"] == "field_verified"
            finally:
                await _delete(VerificationRecordModel, record_id)
                await _delete_new_outbox_events(existing_outbox_events)
