# backend/src/naka/enquiry/infrastructure/locality_lookup.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from naka.catalog.infrastructure.repositories import SqlAlchemyLocalityRepository
from naka.shared.domain.ids import LocalityId


class SqlLocalityNameLookup:
    """Implements enquiry's LocalityLookupPort by reusing catalog's own
    repository internally - infra-to-infra reuse across contexts is normal
    in this single-database modular monolith. What it returns is just a
    name, so catalog.domain.Locality never crosses into enquiry's
    application layer (see LocalityLookupPort's docstring)."""

    def __init__(self, session: AsyncSession) -> None:
        self._localities = SqlAlchemyLocalityRepository(session)

    async def get_name(self, locality_id: LocalityId) -> str | None:
        locality = await self._localities.get(locality_id)
        return locality.name_mr if locality is not None else None
