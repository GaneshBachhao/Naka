# backend/src/naka/catalog/domain/value_objects.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, tzinfo
from enum import IntEnum
from zoneinfo import ZoneInfo

IST: tzinfo = ZoneInfo("Asia/Kolkata")


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"latitude out of range: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"longitude out of range: {self.longitude}")


@dataclass(frozen=True)
class DayHours:
    """A single weekday's trading hours, with an optional midday closure."""

    open_time: time | None
    close_time: time | None
    midday_break_start: time | None = None
    midday_break_end: time | None = None

    @classmethod
    def closed(cls) -> DayHours:
        return cls(open_time=None, close_time=None)

    @property
    def is_closed(self) -> bool:
        return self.open_time is None or self.close_time is None

    def __post_init__(self) -> None:
        if self.is_closed:
            if self.midday_break_start is not None or self.midday_break_end is not None:
                raise ValueError("a closed day cannot have a midday break")
            return

        assert self.open_time is not None and self.close_time is not None  # narrowed by is_closed
        if self.open_time >= self.close_time:
            raise ValueError("open_time must be before close_time")

        has_break = self.midday_break_start is not None or self.midday_break_end is not None
        if has_break:
            if self.midday_break_start is None or self.midday_break_end is None:
                raise ValueError("midday break needs both a start and an end, or neither")
            if not (
                self.open_time <= self.midday_break_start < self.midday_break_end <= self.close_time
            ):
                raise ValueError("midday break must fall strictly within open_time..close_time")

    def is_open_at(self, moment: time) -> bool:
        if self.open_time is None or self.close_time is None:
            return False
        if not (self.open_time <= moment < self.close_time):
            return False
        return not (
            self.midday_break_start is not None
            and self.midday_break_end is not None
            and self.midday_break_start <= moment < self.midday_break_end
        )


@dataclass(frozen=True)
class OpeningHours:
    by_day: dict[Weekday, DayHours] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = set(Weekday) - set(self.by_day)
        if missing:
            names = ", ".join(day.name for day in sorted(missing))
            raise ValueError(f"OpeningHours is missing days: {names}")

    def is_open_at(self, moment: datetime) -> bool:
        # Opening hours are inherently local (IST). A moment must already be
        # timezone-aware UTC (per repo convention) — converting a naive
        # datetime here would silently assume the system's local timezone,
        # which is exactly the kind of bug this domain must not have.
        if moment.tzinfo is None:
            raise ValueError("moment must be timezone-aware")
        ist_moment = moment.astimezone(IST)
        day = Weekday(ist_moment.weekday())
        return self.by_day[day].is_open_at(ist_moment.time())


@dataclass(frozen=True)
class CategoryNames:
    mr: str
    hi: str
    en: str
    synonyms_mr: tuple[str, ...] = ()
    synonyms_hi: tuple[str, ...] = ()
    synonyms_en: tuple[str, ...] = ()
    transliterations: tuple[str, ...] = ()
