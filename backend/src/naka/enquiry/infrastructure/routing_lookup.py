# backend/src/naka/enquiry/infrastructure/routing_lookup.py
from __future__ import annotations

import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from naka.enquiry.application.ports import RoutingCandidateContact
from naka.enquiry.domain.services import RoutingCandidate
from naka.shared.application.ports import Clock
from naka.shared.domain.ids import BusinessId, CategoryId, LocalityId
from naka.shared.domain.phone_number import PhoneNumber

_NEVER_VERIFIED_RECENCY_DAYS = 10_000  # sorts dead last, never picked over a real record

_LOCALITY_CENTROID_QUERY = text(
    "SELECT latitude, longitude FROM catalog_localities WHERE id = :locality_id"
)

# Candidates: routable category, same region as the target locality,
# published+verified+contactable (mirrors Business.can_receive_enquiries(),
# which enquiry's domain can't check itself since it can't import
# catalog.domain - see RoutingCandidate's docstring in enquiry/domain/services.py).
# Response rate and verification recency come from this context's own
# enquiry_routed_requests table and a join into verification_records;
# geographic distance is computed in Python below since a small taluka's
# worth of candidates doesn't need a spatial index or a Postgres geo
# extension for a haversine calculation.
_CANDIDATES_QUERY = text("""
    SELECT
        b.id AS business_id,
        b.latitude,
        b.longitude,
        b.whatsapp_number,
        COALESCE(rr_stats.total_routed, 0) AS total_routed,
        COALESCE(rr_stats.total_responded, 0) AS total_responded,
        vr_stats.last_verified_at
    FROM catalog_businesses b
    JOIN catalog_categories c ON c.id = ANY(b.category_ids)
    LEFT JOIN (
        SELECT business_id,
               COUNT(*) AS total_routed,
               COUNT(*) FILTER (WHERE responded_at IS NOT NULL) AS total_responded
        FROM enquiry_routed_requests
        GROUP BY business_id
    ) rr_stats ON rr_stats.business_id = b.id
    LEFT JOIN (
        SELECT business_id, MAX(verified_at) AS last_verified_at
        FROM verification_records
        GROUP BY business_id
    ) vr_stats ON vr_stats.business_id = b.id
    WHERE c.id = :category_id
      AND c.routable = true
      AND b.region_id = (SELECT region_id FROM catalog_localities WHERE id = :locality_id)
      AND b.publication_state = 'published_verified'
      AND b.whatsapp_number IS NOT NULL
""")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


class SqlRoutingCandidateLookupPort:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    async def find_candidates(
        self, category_id: CategoryId, locality_id: LocalityId
    ) -> list[RoutingCandidateContact]:
        centroid = (
            await self._session.execute(
                _LOCALITY_CENTROID_QUERY, {"locality_id": locality_id.value}
            )
        ).first()
        if centroid is None:
            return []

        rows = (
            await self._session.execute(
                _CANDIDATES_QUERY,
                {"category_id": category_id.value, "locality_id": locality_id.value},
            )
        ).all()

        now = self._clock.now()
        results: list[RoutingCandidateContact] = []
        for row in rows:
            response_rate = (row.total_responded / row.total_routed) if row.total_routed else 0.0
            recency_days = (
                (now - row.last_verified_at).days
                if row.last_verified_at is not None
                else _NEVER_VERIFIED_RECENCY_DAYS
            )
            distance_km = _haversine_km(
                centroid.latitude, centroid.longitude, row.latitude, row.longitude
            )
            results.append(
                RoutingCandidateContact(
                    candidate=RoutingCandidate(
                        business_id=BusinessId(row.business_id),
                        category_matches=True,
                        distance_km=distance_km,
                        response_rate=response_rate,
                        verification_recency_days=recency_days,
                    ),
                    whatsapp_number=PhoneNumber(row.whatsapp_number),
                )
            )
        return results
