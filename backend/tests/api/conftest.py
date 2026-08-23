# backend/tests/api/conftest.py
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from naka.main import create_app
from naka.shared.api.security import create_access_token
from naka.shared.infrastructure.settings import Settings
from tests.api.fakes import FakeRedis

TEST_SETTINGS = Settings(jwt_secret="test-secret-at-least-32-bytes-long!!", jwt_algorithm="HS256")


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    # Overriding app.state after entering the context (which runs the real
    # lifespan and its lazy DB/Redis/Anthropic client construction - none of
    # them connect until actually used, which router tests never let happen
    # since every use-case dependency they exercise gets overridden) keeps
    # these tests deterministic regardless of what's in .env locally.
    with TestClient(app) as test_client:
        app.state.settings = TEST_SETTINGS
        app.state.redis = FakeRedis()
        yield test_client


def ops_headers(subject: str = "test-operator") -> dict[str, str]:
    token = create_access_token(subject, TEST_SETTINGS.jwt_secret, TEST_SETTINGS.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}
