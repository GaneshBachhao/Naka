# backend/tests/enquiry/test_value_objects.py
from __future__ import annotations

import pytest

from naka.enquiry.domain.value_objects import RoutingToken
from tests.enquiry.factories import make_parsed_intent


class TestParsedIntent:
    def test_empty_item_text_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_parsed_intent(item_text="  ")

    @pytest.mark.parametrize("confidence", [-0.01, 1.01, 2.0])
    def test_confidence_out_of_range_rejected(self, confidence: float) -> None:
        with pytest.raises(ValueError):
            make_parsed_intent(confidence=confidence)

    @pytest.mark.parametrize("confidence", [0.0, 1.0, 0.5])
    def test_confidence_boundary_accepted(self, confidence: float) -> None:
        make_parsed_intent(confidence=confidence)


class TestRoutingToken:
    def test_tokens_are_unique(self) -> None:
        assert RoutingToken.new() != RoutingToken.new()

    def test_token_is_nonempty(self) -> None:
        assert len(RoutingToken.new().value) > 20
