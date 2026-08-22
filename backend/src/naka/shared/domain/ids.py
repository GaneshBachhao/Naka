# backend/src/naka/shared/domain/ids.py
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class EntityId:
    value: uuid.UUID

    @classmethod
    def new(cls) -> Self:
        return cls(uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)


class RegionId(EntityId):
    pass


class LocalityId(EntityId):
    pass


class CategoryId(EntityId):
    pass


class BusinessId(EntityId):
    pass
