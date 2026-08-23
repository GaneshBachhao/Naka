# backend/src/naka/catalog/api/deps.py
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.application.use_cases import (
    CreateBusiness,
    GetBusiness,
    ListBusinesses,
    ListCategories,
    ListLocalities,
    PublishBusiness,
    UpdateBusiness,
)
from naka.catalog.infrastructure.repositories import (
    SqlAlchemyBusinessRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyLocalityRepository,
)
from naka.shared.api.deps import get_session


def get_business_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyBusinessRepository:
    return SqlAlchemyBusinessRepository(session)


def get_locality_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyLocalityRepository:
    return SqlAlchemyLocalityRepository(session)


def get_category_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyCategoryRepository:
    return SqlAlchemyCategoryRepository(session)


def get_create_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> CreateBusiness:
    return CreateBusiness(businesses)


def get_update_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> UpdateBusiness:
    return UpdateBusiness(businesses)


def get_publish_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> PublishBusiness:
    return PublishBusiness(businesses)


def get_get_business_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> GetBusiness:
    return GetBusiness(businesses)


def get_list_businesses_use_case(
    businesses: SqlAlchemyBusinessRepository = Depends(get_business_repository),
) -> ListBusinesses:
    return ListBusinesses(businesses)


def get_list_localities_use_case(
    localities: SqlAlchemyLocalityRepository = Depends(get_locality_repository),
) -> ListLocalities:
    return ListLocalities(localities)


def get_list_categories_use_case(
    categories: SqlAlchemyCategoryRepository = Depends(get_category_repository),
) -> ListCategories:
    return ListCategories(categories)
