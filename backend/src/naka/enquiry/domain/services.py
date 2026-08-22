# backend/src/naka/enquiry/domain/services.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from naka.shared.domain.ids import BusinessId

_MAX_FANOUT = 5


@dataclass(frozen=True)
class RoutingCandidate:
    """A business already confirmed eligible - Business.can_receive_enquiries()
    passed, checked by the caller - since enquiry's domain can't reach into
    catalog to verify that itself. Eligibility is a precondition of appearing
    here, not something this service re-checks."""

    business_id: BusinessId
    category_matches: bool
    distance_km: float
    response_rate: float
    verification_recency_days: int


def select_businesses_for_routing(candidates: Iterable[RoutingCandidate]) -> tuple[BusinessId, ...]:
    matching = [c for c in candidates if c.category_matches]
    ranked = sorted(
        matching,
        key=lambda c: (c.distance_km, -c.response_rate, c.verification_recency_days),
    )
    return tuple(c.business_id for c in ranked[:_MAX_FANOUT])
