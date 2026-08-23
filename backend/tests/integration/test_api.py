# backend/tests/integration/test_api.py
from __future__ import annotations

import uuid
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from naka.catalog.infrastructure.models import BusinessModel
from naka.enquiry.infrastructure.models import EnquiryModel
from naka.main import create_app
from naka.shared.api.security import create_access_token
from naka.shared.infrastructure.settings import Settings
from naka.verification.infrastructure.models import VerificationRecordModel

pytestmark = pytest.mark.integration

# These don't override any dependency - unlike tests/api/*, which stub the
# use case and so never actually exercise api/deps.py's factory functions.
# The point here is the opposite: prove the real composition root
# (get_session -> repository -> use case -> router) works end to end
# against a real database, the same discipline T5 applied to the ARQ
# worker's wiring. Each test cleans up whatever it commits, using the
# TestClient's own app.state.session_factory before the lifespan shuts it
# down (which disposes the engine on exiting the `with` block).


def _ops_headers() -> dict[str, str]:
    settings = Settings()
    token = create_access_token("integration-test", settings.jwt_secret, settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


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
                async with app.state.session_factory() as session:
                    await session.execute(
                        delete(BusinessModel).where(BusinessModel.id == business_id)
                    )
                    await session.commit()


class TestSubmitEnquiryEndToEnd:
    async def test_creates_a_real_enquiry(self) -> None:
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
                async with app.state.session_factory() as session:
                    await session.execute(delete(EnquiryModel).where(EnquiryModel.id == enquiry_id))
                    await session.commit()


class TestRecordVerificationEndToEnd:
    async def test_creates_a_real_verification_record(self) -> None:
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
                async with app.state.session_factory() as session:
                    await session.execute(
                        delete(VerificationRecordModel).where(
                            VerificationRecordModel.id == record_id
                        )
                    )
                    await session.commit()
