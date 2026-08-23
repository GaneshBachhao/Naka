# backend/src/naka/catalog/api/router.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from naka.catalog.api.deps import (
    get_create_business_use_case,
    get_get_business_use_case,
    get_publish_business_use_case,
)
from naka.catalog.application.dtos import BusinessDTO, CreateBusinessRequest
from naka.catalog.application.errors import BusinessNotFoundError
from naka.catalog.application.use_cases import CreateBusiness, GetBusiness, PublishBusiness
from naka.shared.api.deps import require_ops_auth
from naka.shared.domain.ids import BusinessId

ops_router = APIRouter(
    prefix="/ops/businesses",
    tags=["ops: businesses"],
    dependencies=[Depends(require_ops_auth)],
)


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


@ops_router.get("/{business_id}", response_model=BusinessDTO, summary="Get a business listing")
async def get_business(
    business_id: uuid.UUID,
    use_case: GetBusiness = Depends(get_get_business_use_case),
) -> BusinessDTO:
    try:
        return await use_case.execute(BusinessId(business_id))
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
