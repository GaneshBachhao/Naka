# backend/src/naka/enquiry/infrastructure/repositories.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.value_objects import EnquiryStatus
from naka.enquiry.infrastructure.mappers import enquiry_to_domain, enquiry_to_model
from naka.enquiry.infrastructure.models import EnquiryModel, RoutedRequestModel
from naka.shared.domain.ids import EnquiryId


class SqlAlchemyEnquiryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, enquiry_id: EnquiryId) -> Enquiry | None:
        model = await self._session.get(EnquiryModel, enquiry_id.value)
        return enquiry_to_domain(model) if model is not None else None

    async def get_by_token(self, token: str) -> Enquiry | None:
        stmt = (
            select(EnquiryModel)
            .join(RoutedRequestModel, RoutedRequestModel.enquiry_id == EnquiryModel.id)
            .where(RoutedRequestModel.token == token)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return enquiry_to_domain(model) if model is not None else None

    async def add(self, enquiry: Enquiry) -> None:
        self._session.add(enquiry_to_model(enquiry))

    async def update(self, enquiry: Enquiry) -> None:
        await self._session.merge(enquiry_to_model(enquiry))

    async def list_routed(self) -> list[Enquiry]:
        stmt = select(EnquiryModel).where(EnquiryModel.status == EnquiryStatus.ROUTED.value)
        result = await self._session.execute(stmt)
        return [enquiry_to_domain(model) for model in result.scalars().all()]
