# backend/src/naka/catalog/api/deps.py
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.application.use_cases import CreateBusiness, GetBusiness, PublishBusiness
from naka.catalog.infrastructure.repositories import SqlAlchemyBusinessRepository
from naka.shared.api.deps import get_session


def get_business_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyBusinessRepository:
    return SqlAlchemyBusinessRepository(session)


def get_create_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> CreateBusiness:
    return CreateBusiness(businesses)


def get_publish_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> PublishBusiness:
    return PublishBusiness(businesses)


def get_get_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> GetBusiness:
    return GetBusiness(businesses)
