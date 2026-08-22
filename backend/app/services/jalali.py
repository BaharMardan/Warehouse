"""Gregorian to Jalali (Persian) date conversion.

This is the jalaali-js algorithm, ported line for line, because the frontend
already depends on ``jalaali-js`` for every date it renders. Sharing one
algorithm means a Jalali year computed on the server can never disagree with
the same date rendered in the browser -- which matters here, because the
warehouse-receipt number embeds a Jalali year that must match what the operator
sees on the tally.

Nowruz is the reason this cannot be approximated as ``gregorian_year - 621``:
that shortcut is wrong for roughly the first eighty days of every Gregorian
year. The leap-year breaks below encode the real Persian calendar.

No third-party dependency: the whole algorithm is arithmetic.
"""

from datetime import date, datetime


# Jalali leap-year cycle boundaries, from the jalaali-js reference implementation.
_BREAKS = [
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
    1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
]


def _div(a: int, b: int) -> int:
    """Integer division truncating toward zero, matching JavaScript's ~~(a / b)."""
    return int(a / b)


def _mod(a: int, b: int) -> int:
    """Remainder paired with _div, so _div(a, b) * b + _mod(a, b) == a."""
    return a - _div(a, b) * b


def _jal_cal(jy: int, without_leap: bool = False) -> tuple[int, int, int]:
    """Return (leap, gy, march) for a Jalali year.

    ``march`` is the Gregorian day in March on which that Jalali year starts.
    ``leap`` is the number of years since the last leap year (0 means leap).
    """
    breaks_length = len(_BREAKS)
    gy = jy + 621
    leap_j = -14
    jp = _BREAKS[0]

    if jy < jp or jy >= _BREAKS[breaks_length - 1]:
        raise ValueError(f"Invalid Jalali year {jy}")

    jump = 0
    for index in range(1, breaks_length):
        jm = _BREAKS[index]
        jump = jm - jp
        if jy < jm:
            break
        leap_j = leap_j + _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm

    n = jy - jp
    leap_j = leap_j + _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1

    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g

    leap = -1
    if not without_leap:
        if jump - n < 6:
            n = n - jump + _div(jump + 4, 33) * 33
        leap = _mod(_mod(n + 1, 33) - 1, 4)
        if leap == -1:
            leap = 4

    return leap, gy, march


def _g2d(gy: int, gm: int, gd: int) -> int:
    """Gregorian date to Julian Day Number."""
    d = (
        _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4)
        + _div(153 * _mod(gm + 9, 12) + 2, 5)
        + gd
        - 34840408
    )
    return d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752


def _d2g(jdn: int) -> tuple[int, int, int]:
    """Julian Day Number to Gregorian (gy, gm, gd)."""
    j = 4 * jdn + 139361631
    j = j + _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _d2j(jdn: int) -> tuple[int, int, int]:
    """Julian Day Number to Jalali (jy, jm, jd)."""
    gy = _d2g(jdn)[0]
    jy = gy - 621
    leap, _, march = _jal_cal(jy, without_leap=False)
    jdn1f = _g2d(gy, 3, march)

    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            return jy, 1 + _div(k, 31), _mod(k, 31) + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1

    return jy, 7 + _div(k, 30), _mod(k, 30) + 1


def to_jalali(value: date | datetime) -> tuple[int, int, int]:
    """Convert a Python date/datetime to a (year, month, day) Jalali tuple."""
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        raise TypeError(f"Expected a date or datetime, received {type(value).__name__}")
    return _d2j(_g2d(value.year, value.month, value.day))


def jalali_year(value: date | datetime) -> int:
    """Return only the Jalali year, which is all the receipt number needs."""
    return to_jalali(value)[0]


def format_jalali(value: date | datetime, separator: str = "/") -> str:
    """Format as YYYY/MM/DD in Latin digits, matching the printed documents."""
    jy, jm, jd = to_jalali(value)
    return f"{jy}{separator}{jm:02d}{separator}{jd:02d}"
