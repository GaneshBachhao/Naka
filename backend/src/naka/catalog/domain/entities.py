# backend/src/naka/catalog/domain/entities.py
from __future__ import annotations

import re
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum

from naka.catalog.domain.value_objects import CategoryNames, Coordinates, OpeningHours, Weekday
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PINCODE = re.compile(r"^[1-9]\d{5}$")


class PublicationState(StrEnum):
    DRAFT = "draft"
    PUBLISHED_UNVERIFIED = "published_unverified"
    PUBLISHED_VERIFIED = "published_verified"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class CategoryTier(IntEnum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4


@dataclass(frozen=True)
class Region:
    id: RegionId
    slug: str
    name_mr: str
    name_hi: str
    name_en: str
    district: str
    state: str
    active: bool

    def __post_init__(self) -> None:
        if not _SLUG.match(self.slug):
            raise ValueError(f"Invalid region slug: {self.slug!r}")


@dataclass(frozen=True)
class Locality:
    id: LocalityId
    region_id: RegionId
    name_mr: str
    name_en: str
    transliteration_variants: tuple[str, ...]
    pincode: str
    centroid: Coordinates
    market_day: Weekday | None

    def __post_init__(self) -> None:
        if not _PINCODE.match(self.pincode):
            raise ValueError(f"Invalid Indian pincode: {self.pincode!r}")


@dataclass(frozen=True)
class Category:
    id: CategoryId
    slug: str
    parent_id: CategoryId | None
    names: CategoryNames
    tier: CategoryTier
    routable: bool

    def __post_init__(self) -> None:
        if not _SLUG.match(self.slug):
            raise ValueError(f"Invalid category slug: {self.slug!r}")


@dataclass(frozen=True)
class Business:
    id: BusinessId
    region_id: RegionId
    locality_id: LocalityId
    name_mr: str
    name_en: str
    owner_name: str
    category_ids: tuple[CategoryId, ...]
    contact_numbers: tuple[PhoneNumber, ...]
    whatsapp_number: PhoneNumber | None
    landmark: str
    coordinates: Coordinates
    opening_hours: OpeningHours
    attributes: frozenset[str]
    publication_state: PublicationState

    def is_open_at(self, moment: datetime) -> bool:
        return self.opening_hours.is_open_at(moment)

    def can_receive_enquiries(self, *, routable_category_ids: AbstractSet[CategoryId]) -> bool:
        # A Business only stores category IDs, not Category objects (aggregates
        # reference each other by ID, never by direct object reference), so
        # "routable category" is resolved by the caller and passed in — it's
        # the one input to this rule that Business genuinely cannot know on
        # its own.
        if self.publication_state is not PublicationState.PUBLISHED_VERIFIED:
            return False
        if self.whatsapp_number is None:
            return False
        return any(category_id in routable_category_ids for category_id in self.category_ids)
