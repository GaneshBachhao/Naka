# backend/tests/api/test_enquiry_router.py
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from naka.enquiry.api.deps import (
    get_enquiry_queue_use_case,
    get_list_operator_queue_use_case,
    get_mark_operator_message_sent_use_case,
    get_parse_and_route_enquiry_use_case,
    get_record_business_response_use_case,
    get_routed_request_by_token_use_case,
    get_submit_enquiry_use_case,
)
from naka.enquiry.application.dtos import (
    EnquiryDTO,
    EnquiryQueueItemDTO,
    RecordBusinessResponseResult,
    RoutedRequestPageDTO,
)
from naka.enquiry.application.errors import EnquiryNotFoundError, InsufficientRoutingCandidatesError
from naka.shared.application.ports import OperatorQueueMessage
from tests.api.conftest import ops_headers
from tests.api.fakes import StubUseCase


class TestSubmitEnquiry:
    def test_returns_201_with_the_created_enquiry(self, app: FastAPI, client: TestClient) -> None:
        dto = EnquiryDTO(id=uuid.uuid4(), status="received")
        app.dependency_overrides[get_submit_enquiry_use_case] = lambda: StubUseCase(result=dto)

        response = client.post(
            "/api/enquiries",
            json={
                "region_id": str(uuid.uuid4()),
                "raw_text": "कापसासाठी औषध कोणाकडे आहे?",
                "customer_phone": "9876543210",
            },
        )

        assert response.status_code == 201
        assert response.json()["id"] == str(dto.id)
        assert response.json()["status"] == "received"

    def test_rejects_malformed_request_body(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_submit_enquiry_use_case] = lambda: StubUseCase()
        response = client.post("/api/enquiries", json={"raw_text": "missing region and phone"})
        assert response.status_code == 422

    def test_rate_limits_after_the_configured_threshold(
        self, app: FastAPI, client: TestClient
    ) -> None:
        dto = EnquiryDTO(id=uuid.uuid4(), status="received")
        app.dependency_overrides[get_submit_enquiry_use_case] = lambda: StubUseCase(result=dto)
        body = {
            "region_id": str(uuid.uuid4()),
            "raw_text": "text",
            "customer_phone": "9876543210",
        }

        for _ in range(10):
            assert client.post("/api/enquiries", json=body).status_code == 201
        limited = client.post("/api/enquiries", json=body)

        assert limited.status_code == 429


class TestGetResponsePage:
    def test_returns_page_data_for_a_valid_token(self, app: FastAPI, client: TestClient) -> None:
        dto = RoutedRequestPageDTO(
            outcome="found", raw_text="text", minutes_ago=5, is_expired=False, has_responded=False
        )
        app.dependency_overrides[get_routed_request_by_token_use_case] = lambda: StubUseCase(
            result=dto
        )

        response = client.get("/r/some-token")

        assert response.status_code == 200
        assert response.json()["outcome"] == "found"

    def test_returns_not_found_outcome_for_unknown_token(
        self, app: FastAPI, client: TestClient
    ) -> None:
        app.dependency_overrides[get_routed_request_by_token_use_case] = lambda: StubUseCase(
            result=RoutedRequestPageDTO(outcome="not_found")
        )

        response = client.get("/r/does-not-exist")

        assert response.status_code == 200
        assert response.json()["outcome"] == "not_found"


class TestRecordResponse:
    def test_returns_the_recorded_outcome(self, app: FastAPI, client: TestClient) -> None:
        result = RecordBusinessResponseResult(outcome="recorded", was_first=True)
        stub = StubUseCase(result=result)
        app.dependency_overrides[get_record_business_response_use_case] = lambda: stub

        response = client.post("/r/some-token", json={"kind": "have_it"})

        assert response.status_code == 200
        assert response.json() == {"outcome": "recorded", "was_first": True}
        # the path token, not a body field, is what reaches the use case
        (request,), _ = stub.calls[0]
        assert request.token == "some-token"

    def test_rejects_missing_kind(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_record_business_response_use_case] = lambda: StubUseCase()
        response = client.post("/r/some-token", json={})
        assert response.status_code == 422


class TestOpsAuthRequired:
    def test_enquiry_queue_requires_auth(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_enquiry_queue_use_case] = lambda: StubUseCase(result=[])
        response = client.get("/ops/enquiries")
        assert response.status_code == 401  # HTTPBearer's own missing-credentials response

    def test_enquiry_queue_rejects_garbage_token(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_enquiry_queue_use_case] = lambda: StubUseCase(result=[])
        response = client.get(
            "/ops/enquiries", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401

    def test_enquiry_queue_accepts_a_valid_token(self, app: FastAPI, client: TestClient) -> None:
        items = [
            EnquiryQueueItemDTO(id=uuid.uuid4(), status="routed", raw_text="text", minutes_ago=3)
        ]
        app.dependency_overrides[get_enquiry_queue_use_case] = lambda: StubUseCase(result=items)

        response = client.get("/ops/enquiries", headers=ops_headers())

        assert response.status_code == 200
        assert len(response.json()) == 1


class TestRouteEnquiry:
    def test_returns_the_routed_enquiry(self, app: FastAPI, client: TestClient) -> None:
        dto = EnquiryDTO(id=uuid.uuid4(), status="routed")
        app.dependency_overrides[get_parse_and_route_enquiry_use_case] = lambda: StubUseCase(
            result=dto
        )

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/route", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()["status"] == "routed"

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_parse_and_route_enquiry_use_case] = lambda: StubUseCase(
            exception=EnquiryNotFoundError(uuid.uuid4())
        )

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/route", headers=ops_headers())

        assert response.status_code == 404

    def test_maps_insufficient_candidates_to_409(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_parse_and_route_enquiry_use_case] = lambda: StubUseCase(
            exception=InsufficientRoutingCandidatesError(uuid.uuid4())
        )

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/route", headers=ops_headers())

        assert response.status_code == 409


class TestOperatorQueue:
    def test_list_operator_queue(self, app: FastAPI, client: TestClient) -> None:
        message = OperatorQueueMessage(
            id=uuid.uuid4(),
            recipient_kind="business",
            phone_number="9876543210",
            message="New enquiry",
            created_at=dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
            sent_at=None,
        )
        app.dependency_overrides[get_list_operator_queue_use_case] = lambda: StubUseCase(
            result=[message]
        )

        response = client.get("/ops/operator-queue", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()[0]["phone_number"] == "9876543210"

    def test_mark_sent_returns_204(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_mark_operator_message_sent_use_case] = lambda: StubUseCase()

        response = client.post(
            f"/ops/operator-queue/{uuid.uuid4()}/mark-sent", headers=ops_headers()
        )

        assert response.status_code == 204
