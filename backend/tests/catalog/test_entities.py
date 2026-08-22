# backend/tests/catalog/test_entities.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.catalog.domain.entities import PublicationState
from naka.shared.domain.ids import CategoryId
from tests.catalog.factories import make_business, make_category, make_locality, make_region


class TestRegion:
    def test_valid_slug(self) -> None:
        make_region(slug="sakri")

    @pytest.mark.parametrize("slug", ["Sakri", "sakri_west", " sakri", "-sakri", "sakri-", ""])
    def test_invalid_slug_raises(self, slug: str) -> None:
        with pytest.raises(ValueError):
            make_region(slug=slug)


class TestLocality:
    @pytest.mark.parametrize("pincode", ["424306", "110001"])
    def test_valid_pincode(self, pincode: str) -> None:
        make_locality(pincode=pincode)

    @pytest.mark.parametrize("pincode", ["42430", "0424306", "42430a", "4243066"])
    def test_invalid_pincode_raises(self, pincode: str) -> None:
        with pytest.raises(ValueError):
            make_locality(pincode=pincode)


class TestCategory:
    def test_valid_slug(self) -> None:
        make_category(slug="agri-input-dealer")

    @pytest.mark.parametrize("slug", ["Agri Dealer", "agri_dealer", ""])
    def test_invalid_slug_raises(self, slug: str) -> None:
        with pytest.raises(ValueError):
            make_category(slug=slug)


class TestBusinessIsOpenAt:
    def test_delegates_to_opening_hours(self) -> None:
        business = make_business()
        open_moment = dt.datetime(2026, 8, 24, 6, 0, tzinfo=dt.UTC)  # ~11:30 IST
        closed_moment = dt.datetime(2026, 8, 24, 20, 0, tzinfo=dt.UTC)  # ~01:30 IST next day
        assert business.is_open_at(open_moment) is True
        assert business.is_open_at(closed_moment) is False


class TestBusinessCanReceiveEnquiries:
    def test_true_when_verified_with_whatsapp_and_routable_category(self) -> None:
        category_id = CategoryId.new()
        business = make_business(
            category_ids=(category_id,),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )
        assert business.can_receive_enquiries(routable_category_ids={category_id}) is True

    @pytest.mark.parametrize(
        "state",
        [
            PublicationState.DRAFT,
            PublicationState.PUBLISHED_UNVERIFIED,
            PublicationState.SUSPENDED,
            PublicationState.CLOSED,
        ],
    )
    def test_false_unless_published_verified(self, state: PublicationState) -> None:
        category_id = CategoryId.new()
        business = make_business(category_ids=(category_id,), publication_state=state)
        assert business.can_receive_enquiries(routable_category_ids={category_id}) is False

    def test_published_unverified_never_receives_enquiries(self) -> None:
        # The explicit rule from CLAUDE.md: unverified listings publish
        # immediately but must never receive routed enquiries.
        category_id = CategoryId.new()
        business = make_business(
            category_ids=(category_id,),
            publication_state=PublicationState.PUBLISHED_UNVERIFIED,
        )
        assert business.can_receive_enquiries(routable_category_ids={category_id}) is False

    def test_false_without_whatsapp_number(self) -> None:
        category_id = CategoryId.new()
        business = make_business(
            category_ids=(category_id,),
            whatsapp_number=None,
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )
        assert business.can_receive_enquiries(routable_category_ids={category_id}) is False

    def test_false_when_category_not_routable(self) -> None:
        business = make_business(
            category_ids=(CategoryId.new(),),
            publication_state=PublicationState.PUBLISHED_VERIFIED,
        )
        other_routable = {CategoryId.new()}
        assert business.can_receive_enquiries(routable_category_ids=other_routable) is False


class TestBusinessPublish:
    @pytest.mark.parametrize("state", [PublicationState.DRAFT, PublicationState.SUSPENDED])
    def test_publish_lands_on_unverified(self, state: PublicationState) -> None:
        business = make_business(publication_state=state)
        published = business.publish()
        assert published.publication_state is PublicationState.PUBLISHED_UNVERIFIED

    @pytest.mark.parametrize(
        "state",
        [
            PublicationState.PUBLISHED_UNVERIFIED,
            PublicationState.PUBLISHED_VERIFIED,
            PublicationState.CLOSED,
        ],
    )
    def test_cannot_publish_from_other_states(self, state: PublicationState) -> None:
        business = make_business(publication_state=state)
        with pytest.raises(ValueError):
            business.publish()
