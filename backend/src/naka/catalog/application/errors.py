# backend/src/naka/catalog/application/errors.py
from __future__ import annotations


class BusinessNotFoundError(Exception):
    pass


class RegionNotFoundError(Exception):
    pass
