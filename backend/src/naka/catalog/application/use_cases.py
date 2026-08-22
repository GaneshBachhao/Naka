# backend/src/naka/catalog/application/use_cases.py
from __future__ import annotations

from naka.catalog.application.dtos import BusinessDTO, CreateBusinessRequest
from naka.catalog.application.errors import BusinessNotFoundError
from naka.catalog.application.ports import BusinessRepository
from naka.catalog.domain.entities import Business, PublicationState
from naka.catalog.domain.value_objects import Coordinates, DayHours, OpeningHours, Weekday
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId, RegionId
from naka.shared.domain.phone_number import PhoneNumber


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
        publication_state=business.publication_state.value,
    )


class CreateBusiness:
    def __init__(self, businesses: BusinessRepository) -> None:
        self._businesses = businesses

    async def execute(self, request: CreateBusinessRequest) -> BusinessDTO:
        opening_hours = OpeningHours(
            by_day={
                Weekday(weekday): DayHours(
                    open_time=hours.open_time,
                    close_time=hours.close_time,
                    midday_break_start=hours.midday_break_start,
                    midday_break_end=hours.midday_break_end,
                )
                for weekday, hours in request.opening_hours.items()
            }
        )
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
            opening_hours=opening_hours,
            attributes=frozenset(request.attributes),
            publication_state=PublicationState.DRAFT,
        )
        await self._businesses.add(business)
        return _to_dto(business)


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
