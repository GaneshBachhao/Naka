# backend/tests/enquiry/test_entities.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.enquiry.domain.entities import Enquiry
from naka.enquiry.domain.events import (
    AdviceRequestDeflected,
    EnquiryAnswered,
    EnquiryReceived,
    EnquiryRouted,
    EnquiryUnanswered,
    ResponseReceived,
)
from naka.enquiry.domain.value_objects import EnquiryStatus, ResponseKind
from naka.shared.domain.ids import BusinessId, EnquiryId
from tests.enquiry.factories import (
    NOW,
    make_parsed_enquiry,
    make_parsed_intent,
    make_received_enquiry,
    make_response,
    make_routed_enquiry,
    make_routed_request,
)


class TestReceive:
    def test_status_is_received(self) -> None:
        enquiry = make_received_enquiry()
        assert enquiry.status is EnquiryStatus.RECEIVED

    def test_emits_enquiry_received(self) -> None:
        enquiry, events = Enquiry.receive(
            id=EnquiryId.new(),
            region_id=make_received_enquiry().region_id,
            raw_text="कापसासाठी औषध कोणाकडे आहे?",
            customer_phone=make_received_enquiry().customer_phone,
            created_at=NOW,
        )
        assert len(events) == 1
        assert isinstance(events[0], EnquiryReceived)
        assert events[0].enquiry_id == enquiry.id

    def test_empty_raw_text_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_received_enquiry(raw_text="   ")

    def test_naive_created_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_received_enquiry(created_at=dt.datetime(2026, 1, 1))


class TestApplyParsedIntent:
    def test_advice_request_is_deflected_not_routed(self) -> None:
        enquiry = make_received_enquiry()
        intent = make_parsed_intent(is_advice_request=True)

        updated, events = enquiry.apply_parsed_intent(intent, NOW)

        assert updated.status is EnquiryStatus.DEFLECTED
        assert len(events) == 1
        assert isinstance(events[0], AdviceRequestDeflected)

    def test_deflected_enquiry_cannot_be_routed(self) -> None:
        enquiry = make_received_enquiry()
        deflected, _ = enquiry.apply_parsed_intent(make_parsed_intent(is_advice_request=True), NOW)

        with pytest.raises(ValueError):
            deflected.route((BusinessId.new(), BusinessId.new(), BusinessId.new()), NOW)

    def test_normal_intent_transitions_to_parsed_and_copies_fields(self) -> None:
        enquiry = make_received_enquiry()
        intent = make_parsed_intent(is_advice_request=False)

        updated, events = enquiry.apply_parsed_intent(intent, NOW)

        assert updated.status is EnquiryStatus.PARSED
        assert updated.category_id == intent.category_id
        assert updated.locality_id == intent.locality_id
        assert updated.urgency == intent.urgency
        assert events == ()  # no domain event defined for a plain parse

    def test_cannot_parse_twice(self) -> None:
        enquiry = make_parsed_enquiry()
        with pytest.raises(ValueError):
            enquiry.apply_parsed_intent(make_parsed_intent(), NOW)


class TestRoute:
    def test_routes_to_each_business(self) -> None:
        enquiry = make_parsed_enquiry()
        ids = (BusinessId.new(), BusinessId.new(), BusinessId.new())

        updated, events = enquiry.route(ids, NOW)

        assert updated.status is EnquiryStatus.ROUTED
        assert {rr.business_id for rr in updated.routed_requests} == set(ids)
        assert len(events) == 1
        assert isinstance(events[0], EnquiryRouted)
        assert events[0].business_ids == ids

    @pytest.mark.parametrize("count", [0, 1, 2, 6, 7])
    def test_rejects_fanout_outside_three_to_five(self, count: int) -> None:
        enquiry = make_parsed_enquiry()
        ids = tuple(BusinessId.new() for _ in range(count))
        with pytest.raises(ValueError):
            enquiry.route(ids, NOW)

    @pytest.mark.parametrize("count", [3, 4, 5])
    def test_accepts_fanout_within_three_to_five(self, count: int) -> None:
        enquiry = make_parsed_enquiry()
        ids = tuple(BusinessId.new() for _ in range(count))
        updated, _ = enquiry.route(ids, NOW)
        assert len(updated.routed_requests) == count

    def test_cannot_route_before_parsing(self) -> None:
        enquiry = make_received_enquiry()
        with pytest.raises(ValueError):
            enquiry.route((BusinessId.new(), BusinessId.new(), BusinessId.new()), NOW)

    def test_each_routed_request_gets_a_unique_token(self) -> None:
        enquiry = make_parsed_enquiry()
        ids = (BusinessId.new(), BusinessId.new(), BusinessId.new())
        updated, _ = enquiry.route(ids, NOW)
        tokens = {rr.token.value for rr in updated.routed_requests}
        assert len(tokens) == 3


class TestRecordResponseRace:
    def test_first_have_it_wins_second_still_recorded(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))

        response_a = make_response(
            business_id=business_a,
            kind=ResponseKind.HAVE_IT,
            responded_at=NOW + dt.timedelta(minutes=2),
        )
        after_a, events_a = enquiry.record_response(response_a, NOW + dt.timedelta(minutes=2))

        assert after_a.status is EnquiryStatus.ANSWERED
        assert after_a.winning_response == response_a
        assert any(isinstance(e, EnquiryAnswered) for e in events_a)
        assert any(isinstance(e, ResponseReceived) for e in events_a)

        response_b = make_response(
            business_id=business_b,
            kind=ResponseKind.HAVE_IT,
            responded_at=NOW + dt.timedelta(minutes=1),
        )
        after_b, events_b = after_a.record_response(response_b, NOW + dt.timedelta(minutes=3))

        # B answered *earlier* in wall-clock time but was *recorded* second -
        # recording order decides the winner, not the responded_at timestamp.
        assert after_b.status is EnquiryStatus.ANSWERED
        assert after_b.winning_response == response_a
        assert response_b in after_b.responses
        assert not any(isinstance(e, EnquiryAnswered) for e in events_b)
        assert any(isinstance(e, ResponseReceived) for e in events_b)

    def test_dont_have_does_not_change_status_or_win(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))

        response = make_response(business_id=business_a, kind=ResponseKind.DONT_HAVE)
        updated, events = enquiry.record_response(response, NOW)

        assert updated.status is EnquiryStatus.ROUTED
        assert updated.winning_response is None
        assert len(events) == 1
        assert isinstance(events[0], ResponseReceived)

    def test_response_from_unrouted_business_rejected(self) -> None:
        enquiry = make_routed_enquiry()
        response = make_response(business_id=BusinessId.new())
        with pytest.raises(ValueError):
            enquiry.record_response(response, NOW)

    def test_duplicate_response_from_same_business_rejected(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        response = make_response(business_id=business_a, kind=ResponseKind.DONT_HAVE)
        updated, _ = enquiry.record_response(response, NOW)

        with pytest.raises(ValueError):
            updated.record_response(response, NOW)

    def test_cannot_respond_before_routing(self) -> None:
        enquiry = make_parsed_enquiry()
        response = make_response()
        with pytest.raises(ValueError):
            enquiry.record_response(response, NOW)


class TestExpire:
    def test_no_op_when_not_routed(self) -> None:
        enquiry = make_parsed_enquiry()
        updated, events = enquiry.expire(NOW + dt.timedelta(hours=1))
        assert updated is enquiry
        assert events == ()

    def test_no_op_before_all_requests_settle(self) -> None:
        enquiry = make_routed_enquiry()
        # reply_window defaults to 30 minutes; well before that, nothing expires
        updated, events = enquiry.expire(NOW + dt.timedelta(minutes=1))
        assert updated is enquiry
        assert events == ()

    def test_becomes_unanswered_once_all_requests_expire(self) -> None:
        enquiry = make_routed_enquiry()
        past_window = NOW + dt.timedelta(minutes=31)

        updated, events = enquiry.expire(past_window)

        assert updated.status is EnquiryStatus.UNANSWERED
        assert len(events) == 1
        assert isinstance(events[0], EnquiryUnanswered)

    def test_no_op_if_any_request_still_pending(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        # business_a answers before the window closes
        response = make_response(
            business_id=business_a,
            kind=ResponseKind.DONT_HAVE,
            responded_at=NOW + dt.timedelta(minutes=5),
        )
        answered_one, _ = enquiry.record_response(response, NOW + dt.timedelta(minutes=5))

        # b and c haven't expired yet
        updated, events = answered_one.expire(NOW + dt.timedelta(minutes=10))
        assert updated is answered_one
        assert events == ()

    def test_already_answered_enquiry_never_becomes_unanswered(self) -> None:
        business_a, business_b, business_c = BusinessId.new(), BusinessId.new(), BusinessId.new()
        enquiry = make_routed_enquiry(business_ids=(business_a, business_b, business_c))
        response = make_response(
            business_id=business_a,
            kind=ResponseKind.HAVE_IT,
            responded_at=NOW + dt.timedelta(minutes=5),
        )
        answered, _ = enquiry.record_response(response, NOW + dt.timedelta(minutes=5))

        updated, events = answered.expire(NOW + dt.timedelta(hours=2))
        assert updated is answered
        assert events == ()


class TestRoutedRequestValidation:
    def test_expires_at_must_be_after_sent_at(self) -> None:
        with pytest.raises(ValueError):
            make_routed_request(sent_at=NOW, expires_at=NOW)

    def test_naive_sent_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_routed_request(sent_at=dt.datetime(2026, 1, 1))

    def test_naive_expires_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_routed_request(expires_at=dt.datetime(2026, 1, 1))

    def test_naive_responded_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_routed_request(responded_at=dt.datetime(2026, 1, 1))

    def test_naive_now_rejected_by_is_expired_at(self) -> None:
        request = make_routed_request()
        with pytest.raises(ValueError):
            request.is_expired_at(dt.datetime(2026, 1, 1))

    def test_is_expired_boundary(self) -> None:
        request = make_routed_request(sent_at=NOW, expires_at=NOW + dt.timedelta(minutes=30))
        assert (
            request.is_expired_at(NOW + dt.timedelta(minutes=30) - dt.timedelta(seconds=1)) is False
        )
        assert request.is_expired_at(NOW + dt.timedelta(minutes=30)) is True

    def test_is_settled_when_responded_even_if_not_expired(self) -> None:
        request = make_routed_request(
            sent_at=NOW,
            expires_at=NOW + dt.timedelta(minutes=30),
            responded_at=NOW + dt.timedelta(minutes=5),
        )
        assert request.is_settled_at(NOW + dt.timedelta(minutes=10)) is True


class TestBusinessResponseValidation:
    def test_can_arrange_by_requires_date(self) -> None:
        with pytest.raises(ValueError):
            make_response(kind=ResponseKind.CAN_ARRANGE_BY, can_arrange_by=None)

    def test_can_arrange_by_accepts_date(self) -> None:
        make_response(kind=ResponseKind.CAN_ARRANGE_BY, can_arrange_by=dt.date(2026, 6, 5))

    def test_other_kinds_reject_can_arrange_by_date(self) -> None:
        with pytest.raises(ValueError):
            make_response(kind=ResponseKind.HAVE_IT, can_arrange_by=dt.date(2026, 6, 5))

    def test_negative_price_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_response(price_paise=-100)

    def test_naive_responded_at_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_response(responded_at=dt.datetime(2026, 1, 1))
