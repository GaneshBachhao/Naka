# backend/tests/catalog/factories.py
from __future__ import annotations

import dataclasses
from datetime import time

from naka.catalog.domain.entities import (
    Business,
    Category,
    CategoryTier,
    Locality,
    PublicationState,
    Region,
)
from naka.catalog.domain.value_objects import (
    CategoryNames,
    Coordinates,
    DayHours,
    OpeningHours,
    Weekday,
)
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


def daily_hours(open_time: time = time(9, 0), close_time: time = time(21, 0)) -> OpeningHours:
    hours = DayHours(open_time=open_time, close_time=close_time)
    return OpeningHours(by_day={day: hours for day in Weekday})


def make_region(**overrides: object) -> Region:
    region = Region(
        id=RegionId.new(),
        slug="sakri",
        name_mr="साक्री",
        name_hi="साक्री",
        name_en="Sakri",
        district="Dhule",
        state="Maharashtra",
        active=True,
    )
    return dataclasses.replace(region, **overrides) if overrides else region


def make_locality(**overrides: object) -> Locality:
    locality = Locality(
        id=LocalityId.new(),
        region_id=RegionId.new(),
        name_mr="पिंपळनेर",
        name_en="Pimpalner",
        transliteration_variants=("pimpalner", "pimplaner"),
        pincode="424306",
        centroid=Coordinates(latitude=20.97, longitude=73.99),
        market_day=Weekday.SUNDAY,
    )
    return dataclasses.replace(locality, **overrides) if overrides else locality


def make_category(**overrides: object) -> Category:
    category = Category(
        id=CategoryId.new(),
        slug="pesticide-dealer",
        parent_id=None,
        names=CategoryNames(mr="कृषी सेवा केंद्र", hi="कृषि सेवा केंद्र", en="Agri-input dealer"),
        tier=CategoryTier.TIER_1,
        routable=True,
    )
    return dataclasses.replace(category, **overrides) if overrides else category


def make_business(**overrides: object) -> Business:
    business = Business(
        id=BusinessId.new(),
        region_id=RegionId.new(),
        locality_id=LocalityId.new(),
        name_mr="साई कृषी केंद्र",
        name_en="Sai Krushi Kendra",
        owner_name="Ramesh Patil",
        category_ids=(CategoryId.new(),),
        contact_numbers=(PhoneNumber("9876543210"),),
        whatsapp_number=PhoneNumber("9876543210"),
        landmark="Bus stand road",
        coordinates=Coordinates(latitude=21.15, longitude=74.33),
        opening_hours=daily_hours(),
        attributes=frozenset(),
        publication_state=PublicationState.PUBLISHED_VERIFIED,
    )
    return dataclasses.replace(business, **overrides) if overrides else business
