# backend/tests/shared/test_deps.py
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from naka.shared.api.deps import get_session


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


def _fake_request(session: _FakeSession) -> Any:
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(session_factory=lambda: session))
    )


class TestGetSession:
    async def test_commits_when_the_request_completes_cleanly(self) -> None:
        session = _FakeSession()
        generator = get_session(_fake_request(session))

        yielded = await anext(generator)
        assert yielded is session

        with pytest.raises(StopAsyncIteration):
            await anext(generator)  # drives the generator past its yield, like FastAPI does

        assert session.committed is True
        assert session.rolled_back is False

    async def test_rolls_back_instead_of_committing_when_the_request_raises(self) -> None:
        # Mirrors exactly what FastAPI's dependency machinery does when the
        # endpoint (or another dependency) raises mid-request: it throws
        # the exception back into the generator at the yield point.
        session = _FakeSession()
        generator = get_session(_fake_request(session))
        await anext(generator)

        with pytest.raises(RuntimeError, match="boom"):
            await generator.athrow(RuntimeError("boom"))

        assert session.rolled_back is True
        assert session.committed is False
