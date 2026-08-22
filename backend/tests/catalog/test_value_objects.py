# backend/tests/catalog/test_value_objects.py
from __future__ import annotations

import datetime as dt

import pytest

from naka.catalog.domain.value_objects import Coordinates, DayHours, OpeningHours, Weekday


class TestCoordinates:
    def test_valid_coordinates(self) -> None:
        Coordinates(latitude=21.15, longitude=74.33)

    @pytest.mark.parametrize("latitude", [-90.0, 90.0])
    def test_latitude_boundary_is_valid(self, latitude: float) -> None:
        Coordinates(latitude=latitude, longitude=0.0)

    @pytest.mark.parametrize("latitude", [-90.0001, 90.0001, 200.0])
    def test_latitude_out_of_range_raises(self, latitude: float) -> None:
        with pytest.raises(ValueError):
            Coordinates(latitude=latitude, longitude=0.0)

    @pytest.mark.parametrize("longitude", [-180.0001, 180.0001])
    def test_longitude_out_of_range_raises(self, longitude: float) -> None:
        with pytest.raises(ValueError):
            Coordinates(latitude=0.0, longitude=longitude)


class TestDayHours:
    def test_closed_day_is_never_open(self) -> None:
        hours = DayHours.closed()
        assert hours.is_closed
        assert hours.is_open_at(dt.time(12, 0)) is False

    def test_closed_day_with_midday_break_raises(self) -> None:
        with pytest.raises(ValueError):
            DayHours(
                open_time=None,
                close_time=None,
                midday_break_start=dt.time(13, 0),
                midday_break_end=dt.time(14, 0),
            )

    def test_open_time_after_close_time_raises(self) -> None:
        with pytest.raises(ValueError):
            DayHours(open_time=dt.time(21, 0), close_time=dt.time(9, 0))

    def test_open_time_equal_close_time_raises(self) -> None:
        with pytest.raises(ValueError):
            DayHours(open_time=dt.time(9, 0), close_time=dt.time(9, 0))

    def test_one_sided_midday_break_raises(self) -> None:
        with pytest.raises(ValueError):
            DayHours(
                open_time=dt.time(9, 0),
                close_time=dt.time(21, 0),
                midday_break_start=dt.time(13, 0),
                midday_break_end=None,
            )

    def test_midday_break_outside_open_hours_raises(self) -> None:
        with pytest.raises(ValueError):
            DayHours(
                open_time=dt.time(9, 0),
                close_time=dt.time(21, 0),
                midday_break_start=dt.time(8, 0),
                midday_break_end=dt.time(9, 30),
            )

    def test_simple_window_boundaries(self) -> None:
        hours = DayHours(open_time=dt.time(9, 0), close_time=dt.time(21, 0))
        assert hours.is_open_at(dt.time(9, 0)) is True  # open boundary inclusive
        assert hours.is_open_at(dt.time(20, 59)) is True
        assert hours.is_open_at(dt.time(21, 0)) is False  # close boundary exclusive
        assert hours.is_open_at(dt.time(8, 59)) is False

    def test_midday_closure_boundaries(self) -> None:
        hours = DayHours(
            open_time=dt.time(9, 0),
            close_time=dt.time(21, 0),
            midday_break_start=dt.time(13, 0),
            midday_break_end=dt.time(14, 0),
        )
        assert hours.is_open_at(dt.time(12, 59)) is True
        assert hours.is_open_at(dt.time(13, 0)) is False  # break start inclusive
        assert hours.is_open_at(dt.time(13, 59)) is False
        assert hours.is_open_at(dt.time(14, 0)) is True  # break end exclusive (reopened)


class TestOpeningHours:
    def _full_week(
        self, overrides: dict[Weekday, DayHours] | None = None
    ) -> dict[Weekday, DayHours]:
        overrides = overrides or {}
        base = {day: DayHours.closed() for day in Weekday}
        base.update(overrides)
        return base

    def test_missing_day_raises(self) -> None:
        incomplete = {day: DayHours.closed() for day in Weekday if day != Weekday.SUNDAY}
        with pytest.raises(ValueError):
            OpeningHours(by_day=incomplete)

    def test_naive_datetime_rejected(self) -> None:
        hours = OpeningHours(by_day=self._full_week())
        naive = dt.datetime(2026, 8, 24, 12, 0)  # no tzinfo
        with pytest.raises(ValueError):
            hours.is_open_at(naive)

    def test_is_open_at_respects_weekday(self) -> None:
        open_hours = DayHours(open_time=dt.time(9, 0), close_time=dt.time(21, 0))
        by_day = self._full_week({Weekday.MONDAY: open_hours, Weekday.TUESDAY: DayHours.closed()})
        hours = OpeningHours(by_day=by_day)

        monday = self._nearest_weekday(Weekday.MONDAY)
        moment = dt.datetime.combine(monday, dt.time(12, 0), tzinfo=dt.UTC).astimezone(
            dt.timezone(dt.timedelta(hours=5, minutes=30))
        )
        assert hours.is_open_at(moment) is True

    def test_ist_conversion_shifts_weekday_across_utc_midnight(self) -> None:
        # IST is UTC+5:30. A UTC moment late on Monday can already be past
        # midnight on Tuesday in IST — is_open_at must use the IST weekday,
        # not the UTC one, or this resolves to the wrong day's hours.
        monday_open_all_day = DayHours(open_time=dt.time(0, 0), close_time=dt.time(23, 59))
        by_day = self._full_week(
            {Weekday.MONDAY: monday_open_all_day, Weekday.TUESDAY: DayHours.closed()}
        )
        hours = OpeningHours(by_day=by_day)

        monday = self._nearest_weekday(Weekday.MONDAY)
        # 19:00 UTC Monday == 00:30 IST Tuesday
        utc_moment = dt.datetime(monday.year, monday.month, monday.day, 19, 0, tzinfo=dt.UTC)

        assert utc_moment.astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).weekday() == (
            Weekday.TUESDAY
        )
        assert hours.is_open_at(utc_moment) is False  # Tuesday's closed, though UTC is still Monday

    @staticmethod
    def _nearest_weekday(target: Weekday) -> dt.date:
        today = dt.date.today()
        delta = (target - today.weekday()) % 7
        return today + dt.timedelta(days=delta)
