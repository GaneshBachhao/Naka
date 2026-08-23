# backend/src/naka/catalog/api/router.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from naka.catalog.api.deps import (
    get_create_business_use_case,
    get_get_business_use_case,
    get_list_businesses_use_case,
    get_list_categories_use_case,
    get_list_localities_use_case,
    get_publish_business_use_case,
    get_region_by_slug_use_case,
    get_update_business_use_case,
)
from naka.catalog.application.dtos import (
    BusinessDTO,
    CategoryDTO,
    CreateBusinessRequest,
    LocalityDTO,
    RegionDTO,
    UpdateBusinessRequest,
)
from naka.catalog.application.errors import BusinessNotFoundError, RegionNotFoundError
from naka.catalog.application.use_cases import (
    CreateBusiness,
    GetBusiness,
    GetRegionBySlug,
    ListBusinesses,
    ListCategories,
    ListLocalities,
    PublishBusiness,
    UpdateBusiness,
)
from naka.shared.api.deps import require_ops_auth
from naka.shared.api.rate_limit import rate_limit
from naka.shared.domain.ids import BusinessId, RegionId

_region_lookup_rate_limit = rate_limit(limit=60, window_seconds=60)

public_router = APIRouter(tags=["regions"])

ops_router = APIRouter(
    prefix="/ops/businesses",
    tags=["ops: businesses"],
    dependencies=[Depends(require_ops_auth)],
)

ops_catalog_router = APIRouter(
    prefix="/ops",
    tags=["ops: catalog"],
    dependencies=[Depends(require_ops_auth)],
)


@public_router.get(
    "/api/regions/{slug}",
    response_model=RegionDTO,
    summary="Look up a region by slug - backs the public site's /[region] route",
    dependencies=[Depends(_region_lookup_rate_limit)],
)
async def get_region(
    slug: str,
    use_case: GetRegionBySlug = Depends(get_region_by_slug_use_case),
) -> RegionDTO:
    try:
        return await use_case.execute(slug)
    except RegionNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Region not found") from exc


@ops_router.post(
    "",
    response_model=BusinessDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a business listing (draft)",
)
async def create_business(
    request: CreateBusinessRequest,
    use_case: CreateBusiness = Depends(get_create_business_use_case),
) -> BusinessDTO:
    return await use_case.execute(request)


@ops_router.get("", response_model=list[BusinessDTO], summary="List all business listings")
async def list_businesses(
    use_case: ListBusinesses = Depends(get_list_businesses_use_case),
) -> list[BusinessDTO]:
    return await use_case.execute()


@ops_router.get("/{business_id}", response_model=BusinessDTO, summary="Get a business listing")
async def get_business(
    business_id: uuid.UUID,
    use_case: GetBusiness = Depends(get_get_business_use_case),
) -> BusinessDTO:
    try:
        return await use_case.execute(BusinessId(business_id))
    except BusinessNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found") from exc


@ops_router.put(
    "/{business_id}",
    response_model=BusinessDTO,
    summary="Edit a business listing's details",
)
async def update_business(
    business_id: uuid.UUID,
    request: UpdateBusinessRequest,
    use_case: UpdateBusiness = Depends(get_update_business_use_case),
) -> BusinessDTO:
    try:
        return await use_case.execute(BusinessId(business_id), request)
    except BusinessNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found") from exc


@ops_router.post(
    "/{business_id}/publish",
    response_model=BusinessDTO,
    summary="Publish a draft or suspended business",
)
async def publish_business(
    business_id: uuid.UUID,
    use_case: PublishBusiness = Depends(get_publish_business_use_case),
) -> BusinessDTO:
    try:
        return await use_case.execute(BusinessId(business_id))
    except BusinessNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found") from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@ops_catalog_router.get(
    "/localities", response_model=list[LocalityDTO], summary="List localities in a region"
)
async def list_localities(
    region_id: uuid.UUID,
    use_case: ListLocalities = Depends(get_list_localities_use_case),
) -> list[LocalityDTO]:
    return await use_case.execute(RegionId(region_id))


@ops_catalog_router.get(
    "/categories", response_model=list[CategoryDTO], summary="List the category tree"
)
async def list_categories(
    use_case: ListCategories = Depends(get_list_categories_use_case),
) -> list[CategoryDTO]:
    return await use_case.execute()
