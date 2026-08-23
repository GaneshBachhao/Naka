# backend/tests/api/test_catalog_router.py
from __future__ import annotations

import uuid
from datetime import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from naka.catalog.api.deps import (
    get_create_business_use_case,
    get_get_business_use_case,
    get_publish_business_use_case,
)
from naka.catalog.application.dtos import BusinessDTO
from naka.catalog.application.errors import BusinessNotFoundError
from tests.api.conftest import ops_headers
from tests.api.fakes import StubUseCase


def _dto(**overrides: object) -> BusinessDTO:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        region_id=uuid.uuid4(),
        locality_id=uuid.uuid4(),
        name_mr="साई कृषी केंद्र",
        name_en="Sai Krushi Kendra",
        owner_name="Ramesh Patil",
        category_ids=[uuid.uuid4()],
        contact_numbers=["+919876543210"],
        whatsapp_number="+919876543210",
        landmark="Bus stand road",
        latitude=21.15,
        longitude=74.33,
        publication_state="draft",
    )
    defaults.update(overrides)
    return BusinessDTO(**defaults)  # type: ignore[arg-type]


def _valid_create_body() -> dict[str, object]:
    trading_hours = {"open_time": time(9, 0).isoformat(), "close_time": time(21, 0).isoformat()}
    closed = {"open_time": None, "close_time": None}
    return {
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
        "opening_hours": {str(i): trading_hours for i in range(6)} | {"6": closed},
        "attributes": [],
    }


class TestOpsAuthRequired:
    def test_create_business_requires_auth(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_create_business_use_case] = lambda: StubUseCase(result=_dto())
        response = client.post("/ops/businesses", json=_valid_create_body())
        assert response.status_code == 401


class TestCreateBusiness:
    def test_returns_201_with_the_created_business(self, app: FastAPI, client: TestClient) -> None:
        dto = _dto(name_en="Test Agro Center")
        app.dependency_overrides[get_create_business_use_case] = lambda: StubUseCase(result=dto)

        response = client.post("/ops/businesses", json=_valid_create_body(), headers=ops_headers())

        assert response.status_code == 201
        assert response.json()["name_en"] == "Test Agro Center"


class TestGetBusiness:
    def test_returns_the_business(self, app: FastAPI, client: TestClient) -> None:
        dto = _dto()
        app.dependency_overrides[get_get_business_use_case] = lambda: StubUseCase(result=dto)

        response = client.get(f"/ops/businesses/{dto.id}", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()["id"] == str(dto.id)

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_get_business_use_case] = lambda: StubUseCase(
            exception=BusinessNotFoundError(uuid.uuid4())
        )

        response = client.get(f"/ops/businesses/{uuid.uuid4()}", headers=ops_headers())

        assert response.status_code == 404


class TestPublishBusiness:
    def test_returns_the_published_business(self, app: FastAPI, client: TestClient) -> None:
        dto = _dto(publication_state="published_unverified")
        app.dependency_overrides[get_publish_business_use_case] = lambda: StubUseCase(result=dto)

        response = client.post(f"/ops/businesses/{dto.id}/publish", headers=ops_headers())

        assert response.status_code == 200
        assert response.json()["publication_state"] == "published_unverified"

    def test_maps_not_found_to_404(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_publish_business_use_case] = lambda: StubUseCase(
            exception=BusinessNotFoundError(uuid.uuid4())
        )

        response = client.post(f"/ops/businesses/{uuid.uuid4()}/publish", headers=ops_headers())

        assert response.status_code == 404

    def test_maps_invalid_transition_to_409(self, app: FastAPI, client: TestClient) -> None:
        app.dependency_overrides[get_publish_business_use_case] = lambda: StubUseCase(
            exception=ValueError("cannot publish a business that is published_verified")
        )

        response = client.post(f"/ops/businesses/{uuid.uuid4()}/publish", headers=ops_headers())

        assert response.status_code == 409
