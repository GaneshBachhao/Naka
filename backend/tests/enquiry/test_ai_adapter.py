# backend/tests/enquiry/test_ai_adapter.py
from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import pytest

from naka.catalog.domain.entities import Category
from naka.catalog.domain.entities import Locality as CatalogLocality
from naka.enquiry.domain.value_objects import Urgency
from naka.enquiry.infrastructure.ai_adapter import AnthropicAIAdapter
from naka.shared.domain.ids import RegionId
from tests.catalog.factories import make_category, make_locality


class _FakeCategories:
    def __init__(self, categories: Sequence[Category]) -> None:
        self._categories = categories

    async def list_all(self) -> Sequence[Category]:
        return self._categories


class _FakeLocalities:
    def __init__(self, localities: Sequence[CatalogLocality]) -> None:
        self._localities = localities

    async def list_by_region(self, region_id: RegionId) -> Sequence[CatalogLocality]:
        return self._localities


class _ToolUseBlock:
    def __init__(self, name: str, tool_input: dict[str, Any]) -> None:
        self.type = "tool_use"
        self.name = name
        self.input = tool_input


class _FakeMessages:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.last_call: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> Any:
        self.last_call = kwargs
        return self.response


class _FakeAnthropicClient:
    def __init__(self, response: Any) -> None:
        self.messages = _FakeMessages(response)


def _response_with(**payload: Any) -> Any:
    defaults: dict[str, Any] = dict(
        category_slug="agri-input-dealer",
        item_text="pesticide for cotton",
        locality_name="Pimpalner",
        urgency="normal",
        confidence=0.9,
        is_advice_request=False,
    )
    defaults.update(payload)
    return SimpleNamespace(
        content=[_ToolUseBlock("parsed_enquiry_intent", defaults)],
    )


@pytest.fixture
def category() -> Category:
    return make_category(slug="agri-input-dealer")


@pytest.fixture
def locality() -> CatalogLocality:
    return make_locality(name_en="Pimpalner")


def _make_adapter(
    client: _FakeAnthropicClient, category: Category, locality: CatalogLocality
) -> AnthropicAIAdapter:
    return AnthropicAIAdapter(
        client, _FakeCategories([category]), _FakeLocalities([locality])  # type: ignore[arg-type]
    )


class TestAnthropicAIAdapter:
    async def test_parses_a_normal_availability_question(
        self, category: Category, locality: CatalogLocality
    ) -> None:
        client = _FakeAnthropicClient(_response_with())
        adapter = _make_adapter(client, category, locality)

        intent = await adapter.parse_enquiry_intent("कापसासाठी औषध कोणाकडे आहे?", RegionId.new())

        assert intent.category_id == category.id
        assert intent.locality_id == locality.id
        assert intent.urgency is Urgency.NORMAL
        assert intent.confidence == 0.9
        assert intent.is_advice_request is False

    async def test_flags_an_advice_request(
        self, category: Category, locality: CatalogLocality
    ) -> None:
        client = _FakeAnthropicClient(_response_with(is_advice_request=True))
        adapter = _make_adapter(client, category, locality)

        intent = await adapter.parse_enquiry_intent("कापसाला कोणते औषध वापरावे?", RegionId.new())

        assert intent.is_advice_request is True

    async def test_raises_when_no_categories_seeded(self, locality: CatalogLocality) -> None:
        client = _FakeAnthropicClient(_response_with())
        adapter = AnthropicAIAdapter(client, _FakeCategories([]), _FakeLocalities([locality]))  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="no categories or localities"):
            await adapter.parse_enquiry_intent("text", RegionId.new())

    async def test_raises_when_no_localities_seeded(self, category: Category) -> None:
        client = _FakeAnthropicClient(_response_with())
        adapter = AnthropicAIAdapter(client, _FakeCategories([category]), _FakeLocalities([]))  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="no categories or localities"):
            await adapter.parse_enquiry_intent("text", RegionId.new())

    async def test_raises_when_response_has_no_tool_call(
        self, category: Category, locality: CatalogLocality
    ) -> None:
        client = _FakeAnthropicClient(SimpleNamespace(content=[]))
        adapter = _make_adapter(client, category, locality)

        with pytest.raises(ValueError, match="did not include"):
            await adapter.parse_enquiry_intent("text", RegionId.new())

    async def test_forces_tool_use_and_offers_the_full_taxonomy(
        self, category: Category, locality: CatalogLocality
    ) -> None:
        client = _FakeAnthropicClient(_response_with())
        adapter = _make_adapter(client, category, locality)

        await adapter.parse_enquiry_intent("text", RegionId.new())

        call = client.messages.last_call
        assert call is not None
        assert call["tool_choice"] == {"type": "tool", "name": "parsed_enquiry_intent"}
        [tool] = call["tools"]
        assert category.slug in tool["input_schema"]["properties"]["category_slug"]["enum"]
        assert locality.name_en in tool["input_schema"]["properties"]["locality_name"]["enum"]
