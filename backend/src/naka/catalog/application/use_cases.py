# backend/src/naka/catalog/application/use_cases.py
from __future__ import annotations

import dataclasses

from naka.catalog.application.dtos import (
    BusinessDTO,
    CategoryDTO,
    CreateBusinessRequest,
    DayHoursRequest,
    LocalityDTO,
    RegionDTO,
    UpdateBusinessRequest,
)
from naka.catalog.application.errors import BusinessNotFoundError, RegionNotFoundError
from naka.catalog.application.ports import (
    BusinessRepository,
    CategoryRepository,
    LocalityRepository,
    RegionRepository,
)
from naka.catalog.domain.entities import Business, PublicationState
from naka.catalog.domain.value_objects import Coordinates, DayHours, OpeningHours, Weekday
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


def _opening_hours_from_request(request: dict[int, DayHoursRequest]) -> OpeningHours:
    return OpeningHours(
        by_day={
            Weekday(weekday): DayHours(
                open_time=hours.open_time,
                close_time=hours.close_time,
                midday_break_start=hours.midday_break_start,
                midday_break_end=hours.midday_break_end,
            )
            for weekday, hours in request.items()
        }
    )


def _opening_hours_to_dto(opening_hours: OpeningHours) -> dict[int, DayHoursRequest]:
    return {
        int(weekday): DayHoursRequest(
            open_time=hours.open_time,
            close_time=hours.close_time,
            midday_break_start=hours.midday_break_start,
            midday_break_end=hours.midday_break_end,
        )
        for weekday, hours in opening_hours.by_day.items()
    }


def _to_dto(business: Business) -> BusinessDTO:
    return BusinessDTO(
        id=business.id.value,
        region_id=business.region_id.value,
        locality_id=business.locality_id.value,
        name_mr=business.name_mr,
        name_en=business.name_en,
        owner_name=business.owner_name,
        category_ids=[c.value for c in business.category_ids],
        contact_numbers=[str(p) for p in business.contact_numbers],
        whatsapp_number=str(business.whatsapp_number) if business.whatsapp_number else None,
        landmark=business.landmark,
        latitude=business.coordinates.latitude,
        longitude=business.coordinates.longitude,
        opening_hours=_opening_hours_to_dto(business.opening_hours),
        attributes=sorted(business.attributes),
        publication_state=business.publication_state.value,
    )


class CreateBusiness:
    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self, request: CreateBusinessRequest) -> BusinessDTO:
        business = Business(
            id=BusinessId.new(),
            region_id=RegionId(request.region_id),
            locality_id=LocalityId(request.locality_id),
            name_mr=request.name_mr,
            name_en=request.name_en,
            owner_name=request.owner_name,
            category_ids=tuple(CategoryId(c) for c in request.category_ids),
            contact_numbers=tuple(PhoneNumber(p) for p in request.contact_numbers),
            whatsapp_number=(
                PhoneNumber(request.whatsapp_number) if request.whatsapp_number else None
            ),
            landmark=request.landmark,
            coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
            opening_hours=_opening_hours_from_request(request.opening_hours),
            attributes=frozenset(request.attributes),
            publication_state=PublicationState.DRAFT,
        )
        await self._businesses.add(business)
        return _to_dto(business)


class UpdateBusiness:
    """Plain data curation, not a state-machine transition - unlike
    publish(), there's no invariant here beyond what the value objects
    already enforce, so this reconstructs the entity directly rather than
    adding a domain method for it. publication_state is deliberately
    untouched: that stays PublishBusiness's job."""

    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self, business_id: BusinessId, request: UpdateBusinessRequest) -> BusinessDTO:
        business = await self._businesses.get(business_id)
        if business is None:
            raise BusinessNotFoundError(business_id)
        updated = dataclasses.replace(
            business,
            locality_id=LocalityId(request.locality_id),
            name_mr=request.name_mr,
            name_en=request.name_en,
            owner_name=request.owner_name,
            category_ids=tuple(CategoryId(c) for c in request.category_ids),
            contact_numbers=tuple(PhoneNumber(p) for p in request.contact_numbers),
            whatsapp_number=(
                PhoneNumber(request.whatsapp_number) if request.whatsapp_number else None
            ),
            landmark=request.landmark,
            coordinates=Coordinates(latitude=request.latitude, longitude=request.longitude),
            opening_hours=_opening_hours_from_request(request.opening_hours),
            attributes=frozenset(request.attributes),
        )
        await self._businesses.update(updated)
        return _to_dto(updated)


class ListBusinesses:
    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self) -> list[BusinessDTO]:
        return [_to_dto(b) for b in await self._businesses.list_all()]


class PublishBusiness:
    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self, business_id: BusinessId) -> BusinessDTO:
        business = await self._businesses.get(business_id)
        if business is None:
            raise BusinessNotFoundError(business_id)
        published = business.publish()
        await self._businesses.update(published)
        return _to_dto(published)


class GetBusiness:
    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self, business_id: BusinessId) -> BusinessDTO:
        business = await self._businesses.get(business_id)
        if business is None:
            raise BusinessNotFoundError(business_id)
        return _to_dto(business)


class ListLocalities:
    def __init__(self, localities: LocalityRepository) -> None:
        self._localities = localities

    async def execute(self, region_id: RegionId) -> list[LocalityDTO]:
        return [
            LocalityDTO(
                id=loc.id.value,
                region_id=loc.region_id.value,
                name_mr=loc.name_mr,
                name_en=loc.name_en,
            )
            for loc in await self._localities.list_by_region(region_id)
        ]


class ListCategories:
    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    async def execute(self) -> list[CategoryDTO]:
        return [
            CategoryDTO(
                id=cat.id.value,
                slug=cat.slug,
                name_mr=cat.names.mr,
                name_en=cat.names.en,
                tier=int(cat.tier),
                routable=cat.routable,
            )
            for cat in await self._categories.list_all()
        ]


class GetRegionBySlug:
    """Backs the public site's /[region] route. Inactive regions 404 the
    same as unknown slugs - CLAUDE.md's region_id-on-every-aggregate rule
    means a region can exist in the data model long before (or after) it's
    meant to be publicly reachable."""

    def __init__(self, regions: RegionRepository) -> None:
        self._regions = regions

    async def execute(self, slug: str) -> RegionDTO:
        region = await self._regions.get_by_slug(slug)
        if region is None or not region.active:
            raise RegionNotFoundError(slug)
        return RegionDTO(
            id=region.id.value,
            slug=region.slug,
            name_mr=region.name_mr,
            name_hi=region.name_hi,
            name_en=region.name_en,
            district=region.district,
            state=region.state,
        )
