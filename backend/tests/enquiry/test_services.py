# backend/tests/enquiry/test_services.py
from __future__ import annotations

from naka.enquiry.domain.services import RoutingCandidate, select_businesses_for_routing
from naka.shared.domain.ids import BusinessId


def _candidate(**overrides: object) -> RoutingCandidate:
    defaults: dict[str, object] = dict(
        business_id=BusinessId.new(),
        category_matches=True,
        distance_km=5.0,
        response_rate=0.5,
        verification_recency_days=10,
    )
    defaults.update(overrides)
    return RoutingCandidate(**defaults)  # type: ignore[arg-type]


def test_non_matching_category_is_excluded() -> None:
    matching = _candidate(category_matches=True)
    non_matching = _candidate(category_matches=False)

    selected = select_businesses_for_routing([matching, non_matching])

    assert selected == (matching.business_id,)


def test_closer_business_ranked_first() -> None:
    near = _candidate(distance_km=1.0)
    far = _candidate(distance_km=10.0)

    selected = select_businesses_for_routing([far, near])

    assert selected == (near.business_id, far.business_id)


def test_higher_response_rate_breaks_distance_ties() -> None:
    responsive = _candidate(distance_km=2.0, response_rate=0.9)
    unresponsive = _candidate(distance_km=2.0, response_rate=0.1)

    selected = select_businesses_for_routing([unresponsive, responsive])

    assert selected == (responsive.business_id, unresponsive.business_id)


def test_more_recent_verification_breaks_distance_and_response_rate_ties() -> None:
    recent = _candidate(distance_km=2.0, response_rate=0.5, verification_recency_days=1)
    stale = _candidate(distance_km=2.0, response_rate=0.5, verification_recency_days=90)

    selected = select_businesses_for_routing([stale, recent])

    assert selected == (recent.business_id, stale.business_id)


def test_caps_at_five_even_with_more_eligible_candidates() -> None:
    candidates = [_candidate(distance_km=float(i)) for i in range(8)]

    selected = select_businesses_for_routing(candidates)

    assert len(selected) == 5
    assert selected == tuple(c.business_id for c in candidates[:5])


def test_full_precedence_order() -> None:
    # category match (hard filter) > distance > response_rate > recency
    best = _candidate(distance_km=1.0, response_rate=0.9, verification_recency_days=1)
    closer_but_less_responsive = _candidate(
        distance_km=1.0, response_rate=0.2, verification_recency_days=1
    )
    farther = _candidate(distance_km=5.0, response_rate=0.9, verification_recency_days=1)
    wrong_category = _candidate(distance_km=0.1, category_matches=False)

    selected = select_businesses_for_routing(
        [farther, closer_but_less_responsive, best, wrong_category]
    )

    assert selected == (
        best.business_id,
        closer_but_less_responsive.business_id,
        farther.business_id,
    )
