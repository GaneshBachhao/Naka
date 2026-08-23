# backend/tests/api/test_verification_router.py
from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from naka.verification.api.deps import (
    get_build_reverification_queue_use_case,
    get_record_verification_use_case,
)
from naka.verification.application.dtos import ReverificationQueueItemDTO, VerificationRecordDTO
from tests.api.conftest import ops_headers
from tests.api.fakes import StubUseCase


class TestOpsAuthRequired:
    def test_record_verification_requires_auth(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_record_verification_use_case] = lambda: StubUseCase()
        response = client.post(
            "/ops/verifications",
            json={
                "business_id": str(uuid.uuid4()),
                "tier": "field_verified",
                "method": "field_visit",
                "verified_by": "Agent Ramesh",
            },
        )
        assert response.status_code == 401


class TestRecordVerification:
    def test_returns_201_with_the_recorded_verification(
        self, app: FastAPI, client: TestClient
    ) -> None:
        dto = VerificationRecordDTO(
            id=uuid.uuid4(),
            business_id=uuid.uuid4(),
            tier="field_verified",
            method="field_visit",
            verified_by="Agent Ramesh",
            notes="",
        )
        app.dependency_overrides[get_record_verification_use_case] = lambda: StubUseCase(result=dto)

        response = client.post(
            "/ops/verifications",
            json={
                "business_id": str(dto.business_id),
                "tier": "field_verified",
                "method": "field_visit",
                "verified_by": "Agent Ramesh",
            },
            headers=ops_headers(),
        )

        assert response.status_code == 201
        assert response.json()["tier"] == "field_verified"

    def test_maps_invalid_enum_value_to_422(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_record_verification_use_case] = lambda: StubUseCase(
            exception=ValueError("'owner_self_service' is not a valid VerificationMethod")
        )

        response = client.post(
            "/ops/verifications",
            json={
                "business_id": str(uuid.uuid4()),
                "tier": "field_verified",
                "method": "owner_self_service",
                "verified_by": "Agent Ramesh",
            },
            headers=ops_headers(),
        )

        assert response.status_code == 422


class TestReverificationQueue:
    def test_returns_the_queue(self, app: FastAPI, client: TestClient) -> None:
        item = ReverificationQueueItemDTO(
            business_id=uuid.uuid4(),
            tier="sourced",
            days_until_decay=-5,
            is_paying=False,
            is_routable_category=True,
        )
        app.dependency_overrides[get_build_reverification_queue_use_case] = lambda: StubUseCase(
            result=[item]
        )

        response = client.get("/ops/reverification-queue", headers=ops_headers())

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["is_routable_category"] is True

    def test_requires_auth(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_build_reverification_queue_use_case] = lambda: StubUseCase(
            result=[]
        )
        response = client.get("/ops/reverification-queue")
        assert response.status_code == 401
