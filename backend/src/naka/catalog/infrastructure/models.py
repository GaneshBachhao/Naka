# backend/src/naka/catalog/infrastructure/models.py
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ARRAY, Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from naka.shared.infrastructure.database import Base


class RegionModel(Base):
    __tablename__ = "catalog_regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_mr: Mapped[str] = mapped_column(String(255))
    name_hi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    district: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean)


class LocalityModel(Base):
    __tablename__ = "catalog_localities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name_mr: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    transliteration_variants: Mapped[list[str]] = mapped_column(ARRAY(String))
    pincode: Mapped[str] = mapped_column(String(6))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    market_day: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CategoryModel(Base):
    __tablename__ = "catalog_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name_mr: Mapped[str] = mapped_column(String(255))
    name_hi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    synonyms_mr: Mapped[list[str]] = mapped_column(ARRAY(String))
    synonyms_hi: Mapped[list[str]] = mapped_column(ARRAY(String))
    synonyms_en: Mapped[list[str]] = mapped_column(ARRAY(String))
    transliterations: Mapped[list[str]] = mapped_column(ARRAY(String))
    tier: Mapped[int] = mapped_column(Integer)
    routable: Mapped[bool] = mapped_column(Boolean, index=True)


class BusinessModel(Base):
    __tablename__ = "catalog_businesses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    region_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    locality_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name_mr: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(255))
    category_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    contact_numbers: Mapped[list[str]] = mapped_column(ARRAY(String))
    whatsapp_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    landmark: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    opening_hours: Mapped[dict[str, Any]] = mapped_column(JSONB)
    attributes: Mapped[list[str]] = mapped_column(ARRAY(String))
    publication_state: Mapped[str] = mapped_column(String(32), index=True)
