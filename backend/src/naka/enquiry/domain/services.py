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


def _ranking_key(candidate: RoutingCandidate) -> tuple[float, float, int]:
    return (candidate.distance_km, -candidate.response_rate, candidate.verification_recency_days)


def rank_routing_candidates(candidates: Iterable[RoutingCandidate]) -> tuple[RoutingCandidate, ...]:
    """Full ranked list, uncapped - the ops console's suggestion view needs
    every eligible candidate (so an operator can swap a default pick for an
    alternate), not just the fan-out this select_businesses_for_routing()
    below will actually route to."""
    matching = [c for c in candidates if c.category_matches]
    return tuple(sorted(matching, key=_ranking_key))


def select_businesses_for_routing(candidates: Iterable[RoutingCandidate]) -> tuple[BusinessId, ...]:
    ranked = rank_routing_candidates(candidates)
    return tuple(c.business_id for c in ranked[:_MAX_FANOUT])
