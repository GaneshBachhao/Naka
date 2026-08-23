# backend/tests/catalog/test_use_cases.py
from __future__ import annotations

import uuid
from datetime import time

import pytest

from naka.catalog.application.dtos import (
    CreateBusinessRequest,
    DayHoursRequest,
    UpdateBusinessRequest,
)
from naka.catalog.application.errors import BusinessNotFoundError
from naka.catalog.application.use_cases import (
    CreateBusiness,
    GetBusiness,
    ListBusinesses,
    ListCategories,
    ListLocalities,
    PublishBusiness,
    UpdateBusiness,
)
from naka.catalog.domain.entities import PublicationState
from naka.shared.domain.ids import BusinessId, RegionId
from tests.catalog.factories import make_category, make_locality
from tests.catalog.fakes import (
    FakeBusinessRepository,
    FakeCategoryRepository,
    FakeLocalityRepository,
)


def _valid_request(**overrides: object) -> CreateBusinessRequest:
    open_hours = DayHoursRequest(open_time=None, close_time=None)
    trading_hours = DayHoursRequest(open_time=time(9, 0), close_time=time(21, 0))
    defaults: dict[str, object] = dict(
        region_id=uuid.uuid4(),
        locality_id=uuid.uuid4(),
        name_mr="साई कृषी केंद्र",
        name_en="Sai Krushi Kendra",
        owner_name="Ramesh Patil",
        category_ids=[uuid.uuid4()],
        contact_numbers=["9876543210"],
        whatsapp_number="9876543210",
        landmark="Bus stand road",
        latitude=21.15,
        longitude=74.33,
        opening_hours={i: trading_hours for i in range(6)} | {6: open_hours},
        attributes=[],
    )
    defaults.update(overrides)
    return CreateBusinessRequest(**defaults)  # type: ignore[arg-type]


def _valid_update_request(**overrides: object) -> UpdateBusinessRequest:
    request = _valid_request(**overrides)
    return UpdateBusinessRequest(**request.model_dump(exclude={"region_id"}))


class TestCreateBusiness:
    async def test_creates_business_in_draft_state(self) -> None:
        repo = FakeBusinessRepository()
        use_case = CreateBusiness(repo)

        dto = await use_case.execute(_valid_request())

        assert dto.publication_state == PublicationState.DRAFT.value
        assert len(repo.businesses) == 1

    async def test_persisted_business_matches_request(self) -> None:
        repo = FakeBusinessRepository()
        use_case = CreateBusiness(repo)
        request = _valid_request(name_en="Test Agro Center")

        dto = await use_case.execute(request)

        stored = repo.businesses[BusinessId(dto.id)]
        assert stored.name_en == "Test Agro Center"
        assert stored.whatsapp_number is not None


class TestPublishBusiness:
    async def test_publishes_a_draft_business(self) -> None:
        repo = FakeBusinessRepository()
        created = await CreateBusiness(repo).execute(_valid_request())

        dto = await PublishBusiness(repo).execute(BusinessId(created.id))

        assert dto.publication_state == PublicationState.PUBLISHED_UNVERIFIED.value

    async def test_raises_when_business_not_found(self) -> None:
        repo = FakeBusinessRepository()
        with pytest.raises(BusinessNotFoundError):
            await PublishBusiness(repo).execute(BusinessId.new())

    async def test_raises_when_already_verified(self) -> None:
        repo = FakeBusinessRepository()
        created = await CreateBusiness(repo).execute(_valid_request())
        business_id = BusinessId(created.id)
        await PublishBusiness(repo).execute(business_id)  # -> PUBLISHED_UNVERIFIED

        # publish() only accepts DRAFT/SUSPENDED, so calling it again must raise
        with pytest.raises(ValueError):
            await PublishBusiness(repo).execute(business_id)


class TestGetBusiness:
    async def test_returns_the_business(self) -> None:
        repo = FakeBusinessRepository()
        created = await CreateBusiness(repo).execute(_valid_request(name_en="Test Agro Center"))

        dto = await GetBusiness(repo).execute(BusinessId(created.id))

        assert dto.name_en == "Test Agro Center"

    async def test_raises_when_not_found(self) -> None:
        repo = FakeBusinessRepository()
        with pytest.raises(BusinessNotFoundError):
            await GetBusiness(repo).execute(BusinessId.new())


class TestUpdateBusiness:
    async def test_updates_editable_fields(self) -> None:
        repo = FakeBusinessRepository()
        created = await CreateBusiness(repo).execute(_valid_request(name_en="Old Name"))
        business_id = BusinessId(created.id)

        dto = await UpdateBusiness(repo).execute(
            business_id, _valid_update_request(name_en="New Name", owner_name="New Owner")
        )

        assert dto.name_en == "New Name"
        assert dto.owner_name == "New Owner"

    async def test_never_touches_publication_state(self) -> None:
        repo = FakeBusinessRepository()
        created = await CreateBusiness(repo).execute(_valid_request())
        business_id = BusinessId(created.id)
        await PublishBusiness(repo).execute(business_id)

        dto = await UpdateBusiness(repo).execute(business_id, _valid_update_request())

        assert dto.publication_state == PublicationState.PUBLISHED_UNVERIFIED.value

    async def test_raises_when_not_found(self) -> None:
        repo = FakeBusinessRepository()
        with pytest.raises(BusinessNotFoundError):
            await UpdateBusiness(repo).execute(BusinessId.new(), _valid_update_request())


class TestListBusinesses:
    async def test_returns_every_business(self) -> None:
        repo = FakeBusinessRepository()
        await CreateBusiness(repo).execute(_valid_request(name_en="First"))
        await CreateBusiness(repo).execute(_valid_request(name_en="Second"))

        dtos = await ListBusinesses(repo).execute()

        assert {dto.name_en for dto in dtos} == {"First", "Second"}

    async def test_returns_empty_list_when_none_exist(self) -> None:
        dtos = await ListBusinesses(FakeBusinessRepository()).execute()
        assert dtos == []


class TestListLocalities:
    async def test_returns_only_localities_in_the_requested_region(self) -> None:
        region = RegionId.new()
        in_region = make_locality(region_id=region)
        elsewhere = make_locality()
        repo = FakeLocalityRepository([in_region, elsewhere])

        dtos = await ListLocalities(repo).execute(region)

        assert [dto.id for dto in dtos] == [in_region.id.value]


class TestListCategories:
    async def test_returns_every_category(self) -> None:
        category = make_category()
        repo = FakeCategoryRepository([category])

        dtos = await ListCategories(repo).execute()

        assert [dto.id for dto in dtos] == [category.id.value]
        assert dtos[0].name_mr == category.names.mr
