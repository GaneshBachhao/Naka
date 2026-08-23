# backend/src/naka/catalog/infrastructure/mappers.py
from __future__ import annotations

from datetime import time
from typing import Any

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
from naka.catalog.infrastructure.models import (
    BusinessModel,
    CategoryModel,
    LocalityModel,
    RegionModel,
)
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


def region_to_domain(model: RegionModel) -> Region:
    return Region(
        id=RegionId(model.id),
        slug=model.slug,
        name_mr=model.name_mr,
        name_hi=model.name_hi,
        name_en=model.name_en,
        district=model.district,
        state=model.state,
        active=model.active,
    )


def region_to_model(region: Region) -> RegionModel:
    return RegionModel(
        id=region.id.value,
        slug=region.slug,
        name_mr=region.name_mr,
        name_hi=region.name_hi,
        name_en=region.name_en,
        district=region.district,
        state=region.state,
        active=region.active,
    )


def locality_to_domain(model: LocalityModel) -> Locality:
    return Locality(
        id=LocalityId(model.id),
        region_id=RegionId(model.region_id),
        name_mr=model.name_mr,
        name_en=model.name_en,
        transliteration_variants=tuple(model.transliteration_variants),
        pincode=model.pincode,
        centroid=Coordinates(latitude=model.latitude, longitude=model.longitude),
        market_day=Weekday(model.market_day) if model.market_day is not None else None,
    )


def locality_to_model(locality: Locality) -> LocalityModel:
    return LocalityModel(
        id=locality.id.value,
        region_id=locality.region_id.value,
        name_mr=locality.name_mr,
        name_en=locality.name_en,
        transliteration_variants=list(locality.transliteration_variants),
        pincode=locality.pincode,
        latitude=locality.centroid.latitude,
        longitude=locality.centroid.longitude,
        market_day=int(locality.market_day) if locality.market_day is not None else None,
    )


def category_to_domain(model: CategoryModel) -> Category:
    return Category(
        id=CategoryId(model.id),
        slug=model.slug,
        parent_id=CategoryId(model.parent_id) if model.parent_id else None,
        names=CategoryNames(
            mr=model.name_mr,
            hi=model.name_hi,
            en=model.name_en,
            synonyms_mr=tuple(model.synonyms_mr),
            synonyms_hi=tuple(model.synonyms_hi),
            synonyms_en=tuple(model.synonyms_en),
            transliterations=tuple(model.transliterations),
        ),
        tier=CategoryTier(model.tier),
        routable=model.routable,
    )


def category_to_model(category: Category) -> CategoryModel:
    return CategoryModel(
        id=category.id.value,
        slug=category.slug,
        parent_id=category.parent_id.value if category.parent_id else None,
        name_mr=category.names.mr,
        name_hi=category.names.hi,
        name_en=category.names.en,
        synonyms_mr=list(category.names.synonyms_mr),
        synonyms_hi=list(category.names.synonyms_hi),
        synonyms_en=list(category.names.synonyms_en),
        transliterations=list(category.names.transliterations),
        tier=int(category.tier),
        routable=category.routable,
    )


def _time_to_json(value: time | None) -> str | None:
    return value.isoformat() if value is not None else None


def _time_from_json(value: str | None) -> time | None:
    return time.fromisoformat(value) if value is not None else None


def _opening_hours_to_json(hours: OpeningHours) -> dict[str, Any]:
    return {
        str(int(day)): {
            "open_time": _time_to_json(day_hours.open_time),
            "close_time": _time_to_json(day_hours.close_time),
            "midday_break_start": _time_to_json(day_hours.midday_break_start),
            "midday_break_end": _time_to_json(day_hours.midday_break_end),
        }
        for day, day_hours in hours.by_day.items()
    }


def _opening_hours_from_json(data: dict[str, Any]) -> OpeningHours:
    return OpeningHours(
        by_day={
            Weekday(int(weekday)): DayHours(
                open_time=_time_from_json(day_json["open_time"]),
                close_time=_time_from_json(day_json["close_time"]),
                midday_break_start=_time_from_json(day_json["midday_break_start"]),
                midday_break_end=_time_from_json(day_json["midday_break_end"]),
            )
            for weekday, day_json in data.items()
        }
    )


def business_to_domain(model: BusinessModel) -> Business:
    return Business(
        id=BusinessId(model.id),
        region_id=RegionId(model.region_id),
        locality_id=LocalityId(model.locality_id),
        name_mr=model.name_mr,
        name_en=model.name_en,
        owner_name=model.owner_name,
        category_ids=tuple(CategoryId(c) for c in model.category_ids),
        contact_numbers=tuple(PhoneNumber(c) for c in model.contact_numbers),
        whatsapp_number=PhoneNumber(model.whatsapp_number) if model.whatsapp_number else None,
        landmark=model.landmark,
        coordinates=Coordinates(latitude=model.latitude, longitude=model.longitude),
        opening_hours=_opening_hours_from_json(model.opening_hours),
        attributes=frozenset(model.attributes),
        publication_state=PublicationState(model.publication_state),
    )


def business_to_model(business: Business) -> BusinessModel:
    return BusinessModel(
        id=business.id.value,
        region_id=business.region_id.value,
        locality_id=business.locality_id.value,
        name_mr=business.name_mr,
        name_en=business.name_en,
        owner_name=business.owner_name,
        category_ids=[c.value for c in business.category_ids],
        contact_numbers=[p.value for p in business.contact_numbers],
        whatsapp_number=business.whatsapp_number.value if business.whatsapp_number else None,
        landmark=business.landmark,
        latitude=business.coordinates.latitude,
        longitude=business.coordinates.longitude,
        opening_hours=_opening_hours_to_json(business.opening_hours),
        attributes=list(business.attributes),
        publication_state=business.publication_state.value,
    )
