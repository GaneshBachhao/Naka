# backend/tests/api/test_enquiry_router.py
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from naka.enquiry.api.deps import (
    get_daily_counters_use_case,
    get_enquiry_detail_use_case,
    get_enquiry_queue_use_case,
    get_enquiry_status_use_case,
    get_list_operator_queue_use_case,
    get_mark_operator_message_sent_use_case,
    get_parse_enquiry_use_case,
    get_record_business_response_use_case,
    get_route_enquiry_use_case,
    get_routed_request_by_token_use_case,
    get_submit_enquiry_use_case,
    get_suggest_routing_candidates_use_case,
)
from naka.enquiry.application.dtos import (
    DailyCountersDTO,
    EnquiryDetailDTO,
    EnquiryDTO,
    EnquiryQueueItemDTO,
    EnquiryStatusDTO,
    RecordBusinessResponseResult,
    RoutedMessageDTO,
    RoutedRequestPageDTO,
    RouteEnquiryResult,
    RoutingSuggestionDTO,
    WinningAnswerDTO,
)
from naka.enquiry.application.errors import (
    AIClientUnavailableError,
    EnquiryNotFoundError,
    InsufficientRoutingCandidatesError,
    InvalidRoutingSelectionError,
)
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


class TestGetEnquiryStatus:
    def test_returns_status_for_a_known_enquiry(self, app: FastAPI, client: TestClient) -> None:
        dto = EnquiryStatusDTO(outcome="found", status="routed", minutes_ago=2, routed_count=3)
        app.dependency_overrides[get_enquiry_status_use_case] = lambda: StubUseCase(result=dto)

        response = client.get(f"/api/enquiries/{uuid.uuid4()}/status")

        assert response.status_code == 200
        assert response.json()["status"] == "routed"
        assert response.json()["routed_count"] == 3

    def test_returns_the_winning_answer_once_answered(
        self, app: FastAPI, client: TestClient
    ) -> None:
        dto = EnquiryStatusDTO(
            outcome="found",
            status="answered",
            minutes_ago=6,
            routed_count=3,
            answer=WinningAnswerDTO(price_paise=25000, note="स्टॉकमध्ये आहे"),
        )
        app.dependency_overrides[get_enquiry_status_use_case] = lambda: StubUseCase(result=dto)

        response = client.get(f"/api/enquiries/{uuid.uuid4()}/status")

        assert response.status_code == 200
        assert response.json()["answer"]["price_paise"] == 25000

    def test_returns_not_found_outcome_for_unknown_id(
        self, app: FastAPI, client: TestClient
    ) -> None:
        app.dependency_overrides[get_enquiry_status_use_case] = lambda: StubUseCase(
            result=EnquiryStatusDTO(outcome="not_found")
        )

        response = client.get(f"/api/enquiries/{uuid.uuid4()}/status")

        assert response.status_code == 200
        assert response.json()["outcome"] == "not_found"


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


class TestGetEnquiryDetail:
    def test_returns_the_detail(self, app: FastAPI, client: TestClient) -> None:
        dto = EnquiryDetailDTO(
            id=uuid.uuid4(),
            status="routed",
            raw_text="text",
            region_id=uuid.uuid4(),
            created_at=dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
            minutes_ago=3,
        )
        app.dependency_overrides[get_enquiry_detail_use_case] = lambda: StubUseCase(result=dto)

        response = client.get(f"/ops/enquiries/{uuid.uuid4()}", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()["status"] == "routed"

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_enquiry_detail_use_case] = lambda: StubUseCase(
            exception=EnquiryNotFoundError(uuid.uuid4())
        )

        response = client.get(f"/ops/enquiries/{uuid.uuid4()}", headers=ops_headers())

        assert response.status_code == 404


class TestParseEnquiry:
    def test_returns_the_parsed_enquiry(self, app: FastAPI, client: TestClient) -> None:
        dto = EnquiryDTO(id=uuid.uuid4(), status="parsed")
        app.dependency_overrides[get_parse_enquiry_use_case] = lambda: StubUseCase(result=dto)

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/parse", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()["status"] == "parsed"

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_parse_enquiry_use_case] = lambda: StubUseCase(
            exception=EnquiryNotFoundError(uuid.uuid4())
        )

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/parse", headers=ops_headers())

        assert response.status_code == 404

    def test_maps_ai_client_unavailable_to_502(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_parse_enquiry_use_case] = lambda: StubUseCase(
            exception=AIClientUnavailableError("AI parsing is unavailable: no API key")
        )

        response = client.post(f"/ops/enquiries/{uuid.uuid4()}/parse", headers=ops_headers())

        assert response.status_code == 502


class TestSuggestRoutingCandidates:
    def test_returns_ranked_suggestions(self, app: FastAPI, client: TestClient) -> None:
        suggestion = RoutingSuggestionDTO(
            business_id=uuid.uuid4(),
            distance_km=1.2,
            response_rate=0.8,
            verification_recency_days=5,
            reason="1.2 km away, 80% response rate, verified 5d ago",
            default_selected=True,
        )
        app.dependency_overrides[get_suggest_routing_candidates_use_case] = lambda: StubUseCase(
            result=[suggestion]
        )

        response = client.get(f"/ops/enquiries/{uuid.uuid4()}/candidates", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()[0]["default_selected"] is True

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_suggest_routing_candidates_use_case] = lambda: StubUseCase(
            exception=EnquiryNotFoundError(uuid.uuid4())
        )

        response = client.get(f"/ops/enquiries/{uuid.uuid4()}/candidates", headers=ops_headers())

        assert response.status_code == 404


class TestRouteEnquiry:
    def test_returns_the_routed_enquiry_and_messages(
        self, app: FastAPI, client: TestClient
    ) -> None:
        business_id = uuid.uuid4()
        result = RouteEnquiryResult(
            enquiry=EnquiryDTO(id=uuid.uuid4(), status="routed"),
            messages=[
                RoutedMessageDTO(business_id=business_id, phone_number="9876543210", message="hi")
            ],
        )
        app.dependency_overrides[get_route_enquiry_use_case] = lambda: StubUseCase(result=result)

        response = client.post(
            f"/ops/enquiries/{uuid.uuid4()}/route",
            json={"business_ids": [str(business_id)]},
            headers=ops_headers(),
        )

        assert response.status_code == 200
        assert response.json()["enquiry"]["status"] == "routed"
        assert response.json()["messages"][0]["message"] == "hi"

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_route_enquiry_use_case] = lambda: StubUseCase(
            exception=EnquiryNotFoundError(uuid.uuid4())
        )

        response = client.post(
            f"/ops/enquiries/{uuid.uuid4()}/route",
            json={"business_ids": [str(uuid.uuid4())] * 3},
            headers=ops_headers(),
        )

        assert response.status_code == 404

    def test_maps_insufficient_candidates_to_409(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_route_enquiry_use_case] = lambda: StubUseCase(
            exception=InsufficientRoutingCandidatesError(uuid.uuid4())
        )

        response = client.post(
            f"/ops/enquiries/{uuid.uuid4()}/route",
            json={"business_ids": [str(uuid.uuid4())] * 3},
            headers=ops_headers(),
        )

        assert response.status_code == 409

    def test_maps_invalid_selection_to_409(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_route_enquiry_use_case] = lambda: StubUseCase(
            exception=InvalidRoutingSelectionError(uuid.uuid4())
        )

        response = client.post(
            f"/ops/enquiries/{uuid.uuid4()}/route",
            json={"business_ids": [str(uuid.uuid4())] * 3},
            headers=ops_headers(),
        )

        assert response.status_code == 409

    def test_maps_domain_value_error_to_409(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_route_enquiry_use_case] = lambda: StubUseCase(
            exception=ValueError("fan-out must route to between 3 and 5 businesses")
        )

        response = client.post(
            f"/ops/enquiries/{uuid.uuid4()}/route",
            json={"business_ids": [str(uuid.uuid4())] * 2},
            headers=ops_headers(),
        )

        assert response.status_code == 409


class TestGetDailyCounters:
    def test_returns_the_counters(self, app: FastAPI, client: TestClient) -> None:
        dto = DailyCountersDTO(
            total_enquiries=10, answered=6, answer_rate=0.6, median_response_seconds=420
        )
        app.dependency_overrides[get_daily_counters_use_case] = lambda: StubUseCase(result=dto)

        response = client.get("/ops/counters/daily", headers=ops_headers())

        assert response.status_code == 200
        assert response.json() == {
            "total_enquiries": 10,
            "answered": 6,
            "answer_rate": 0.6,
            "median_response_seconds": 420,
        }


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
