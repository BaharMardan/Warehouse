from datetime import date, datetime, timedelta

import pytest

from app.services.jalali import format_jalali, jalali_year, to_jalali


NOWRUZ = [
    (date(2023, 3, 21), (1402, 1, 1)),
    (date(2024, 3, 20), (1403, 1, 1)),
    (date(2025, 3, 21), (1404, 1, 1)),
    (date(2026, 3, 21), (1405, 1, 1)),
]


@pytest.mark.parametrize("gregorian,expected", NOWRUZ)
def test_nowruz_starts_the_jalali_year(gregorian, expected):
    assert to_jalali(gregorian) == expected


@pytest.mark.parametrize("gregorian,expected", NOWRUZ)
def test_day_before_nowruz_is_the_previous_year(gregorian, expected):
    jy, jm, jd = to_jalali(gregorian - timedelta(days=1))
    assert jy == expected[0] - 1
    assert jm == 12


def test_january_is_still_the_previous_jalali_year():
    # The naive gy - 621 shortcut returns 1405 here, which is wrong: this is
    # exactly the trap the receipt number would fall into for winter tallies.
    assert jalali_year(date(2026, 1, 1)) == 1404


def test_accepts_datetime_as_oracle_returns_it():
    assert to_jalali(datetime(2026, 8, 22, 13, 45)) == (1405, 5, 31)


def test_rejects_non_dates():
    with pytest.raises(TypeError):
        to_jalali("2026-08-22")


def test_format_uses_latin_digits_and_zero_padding():
    assert format_jalali(date(2026, 3, 21)) == "1405/01/01"


def test_days_run_continuously_across_twenty_years():
    """Every step of one Gregorian day must advance the Jalali date by one."""
    current = date(2015, 1, 1)
    end = date(2035, 1, 1)
    previous = to_jalali(current)

    while current < end:
        current += timedelta(days=1)
        jy, jm, jd = to_jalali(current)
        py, pm, pd = previous
        same_month = (jy, jm, jd) == (py, pm, pd + 1)
        next_month = (jy, jm, jd) == (py, pm + 1, 1)
        next_year = (jy, jm, jd) == (py + 1, 1, 1)
        assert same_month or next_month or next_year, f"gap at {current}"
        previous = (jy, jm, jd)
