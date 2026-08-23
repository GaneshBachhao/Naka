# backend/src/naka/enquiry/infrastructure/ai_adapter.py
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

from naka.catalog.domain.entities import Category
from naka.catalog.domain.entities import Locality as CatalogLocality
from naka.enquiry.domain.value_objects import ParsedIntent, Urgency
from naka.shared.domain.ids import RegionId

_SYSTEM_PROMPT = """You are Naka's enquiry intent parser for Sakri taluka, Maharashtra, India. \
Customers write in Marathi, Hindi, or Latin-transliterated Marathi/Hindi (e.g. "kapus" for \
cotton, "aushadh" for medicine). Extract the structured intent from their raw message using \
the parsed_enquiry_intent tool.

CRITICAL SAFETY RULE - is_advice_request:
Naka routes AVAILABILITY questions only ("who has this", "is it in stock", "is the doctor \
sitting") - never ADVICE questions ("what should I use", "which medicine is best", "how much \
dose"). Pesticide advice is regulated under India's Insecticides Act; medical advice is \
obviously out of scope. Set is_advice_request=true whenever the customer is asking WHAT to \
use, WHICH product or treatment is right, or HOW to treat something - not just WHERE to find \
it or WHO has it.

Examples:
- "कापसासाठी औषध कोणाकडे आहे?" (who has medicine for cotton?) -> is_advice_request=false
- "कापसाला कोणते औषध वापरावे?" (which medicine should I use for cotton?) -> is_advice_request=true
- "ताप आहे, कोणते औषध घेऊ?" (I have fever, which medicine should I take?) -> is_advice_request=true
- "paracetamol kuthe milel?" (where can I find paracetamol?) -> is_advice_request=false

When is_advice_request is true, category_slug and locality_name are still required fields -
give your best guess - but the enquiry will not be routed regardless of what you return."""


class CategoryLookupPort(Protocol):
    async def list_all(self) -> Sequence[Category]: ...


class LocalityLookupPort(Protocol):
    async def list_by_region(self, region_id: RegionId) -> Sequence[CatalogLocality]: ...


def _build_tool(category_slugs: Sequence[str], locality_names: Sequence[str]) -> ToolParam:
    return {
        "name": "parsed_enquiry_intent",
        "description": "Structured intent extracted from the customer's raw enquiry text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category_slug": {"type": "string", "enum": list(category_slugs)},
                "item_text": {
                    "type": "string",
                    "description": "The specific item or service being asked about, in the "
                    "customer's own words.",
                },
                "locality_name": {"type": "string", "enum": list(locality_names)},
                "urgency": {"type": "string", "enum": ["normal", "urgent"]},
                "confidence": {
                    "type": "number",
                    "description": "0.0-1.0 confidence in this classification.",
                },
                "is_advice_request": {"type": "boolean"},
            },
            "required": [
                "category_slug",
                "item_text",
                "locality_name",
                "urgency",
                "confidence",
                "is_advice_request",
            ],
        },
    }


def _extract_tool_input(response: Any, tool_name: str) -> dict[str, Any]:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
            return dict(block.input)
    raise ValueError(f"Anthropic response did not include a {tool_name!r} tool call")


class AnthropicAIAdapter:
    """AIClientPort via the Anthropic API. Categories are global, so the full
    list grounds every call; localities are region-scoped. The AI picks by
    slug/name from the actual seeded taxonomy rather than inventing IDs -
    this adapter resolves its choice back to real CategoryId/LocalityId
    values, and raises if it ever picks something outside what was offered
    (which the tool's enum constraint should already prevent)."""

    def __init__(
        self,
        client: AsyncAnthropic,
        categories: CategoryLookupPort,
        localities: LocalityLookupPort,
        model: str = "claude-sonnet-5",
    ) -> None:
        self._client = client
        self._categories = categories
        self._localities = localities
        self._model = model

    async def parse_enquiry_intent(self, raw_text: str, region_id: RegionId) -> ParsedIntent:
        categories = await self._categories.list_all()
        localities = await self._localities.list_by_region(region_id)
        if not categories or not localities:
            raise ValueError("cannot parse intent: no categories or localities are seeded")

        category_by_slug = {category.slug: category.id for category in categories}
        locality_by_name = {locality.name_en: locality.id for locality in localities}

        tool = _build_tool(sorted(category_by_slug), sorted(locality_by_name))
        tool_choice: ToolChoiceToolParam = {"type": "tool", "name": "parsed_enquiry_intent"}
        messages: list[MessageParam] = [{"role": "user", "content": raw_text}]
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[tool],
            tool_choice=tool_choice,
            messages=messages,
        )
        payload = _extract_tool_input(response, "parsed_enquiry_intent")

        return ParsedIntent(
            category_id=category_by_slug[payload["category_slug"]],
            item_text=payload["item_text"],
            locality_id=locality_by_name[payload["locality_name"]],
            urgency=Urgency(payload["urgency"]),
            confidence=float(payload["confidence"]),
            is_advice_request=bool(payload["is_advice_request"]),
        )
