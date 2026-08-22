from datetime import date, datetime

import pytest

from app.services.ghabz_numbering import (
    TallyNotFound,
    TallyNotNumbered,
    allocate_ghabz_number,
)


class _FakeVar:
    def __init__(self):
        self.value = None

    def getvalue(self):
        return self.value


class _FakeTallyCursor:
    """Stands in for an Oracle cursor over one tally and its receipts."""

    def __init__(self, tally_row, highest_sequence=None, now=datetime(2026, 8, 22)):
        self.tally_row = tally_row
        self.highest_sequence = highest_sequence
        self.now = now
        self._result = None
        self.locked = False

    def var(self, _type):
        return _FakeVar()

    def execute(self, sql, params=None):
        if "FOR UPDATE" in sql:
            self.locked = True
            self._result = self.tally_row
        elif "SYSDATE" in sql:
            self._result = (self.now,)
        elif "GHABZ_SEQ" in sql:
            assert 'IS_DELETED' not in sql, "sequence must span soft-deleted receipts"
            self._result = ((self.highest_sequence or 0) + 1,)
        else:
            raise AssertionError(f"unexpected statement: {sql}")

    def fetchone(self):
        return self._result


def test_first_receipt_on_a_tally_starts_at_one():
    cursor = _FakeTallyCursor(("866", datetime(2026, 6, 9), None))

    number, sequence, tali_number = allocate_ghabz_number(cursor, 42)

    assert number == "1405_866_1"
    assert sequence == 1
    assert tali_number == "866"
    assert cursor.locked, "the parent tally row must be locked"


def test_sequence_continues_within_the_same_tally():
    cursor = _FakeTallyCursor(("866", datetime(2026, 6, 9), None), highest_sequence=3)

    assert allocate_ghabz_number(cursor, 42)[0] == "1405_866_4"


def test_year_comes_from_the_tally_not_from_today():
    """A tally opened in Esfand keeps its own year even if issued after Nowruz."""
    cursor = _FakeTallyCursor(
        ("500", datetime(2026, 2, 14), None), now=datetime(2026, 8, 22)
    )

    assert allocate_ghabz_number(cursor, 7)[0] == "1404_500_1"


def test_unloading_date_covers_a_missing_creation_date():
    cursor = _FakeTallyCursor(("900", None, date(2026, 6, 9)))

    assert allocate_ghabz_number(cursor, 8)[0] == "1405_900_1"


def test_falls_back_to_database_time_when_the_tally_has_no_dates():
    cursor = _FakeTallyCursor(("901", None, None), now=datetime(2026, 8, 22))

    assert allocate_ghabz_number(cursor, 9)[0] == "1405_901_1"


def test_missing_tally_is_reported_distinctly():
    cursor = _FakeTallyCursor(None)

    with pytest.raises(TallyNotFound):
        allocate_ghabz_number(cursor, 404)


@pytest.mark.parametrize("tali_number", [None, "", "   "])
def test_unnumbered_tally_cannot_issue_a_receipt(tali_number):
    cursor = _FakeTallyCursor((tali_number, datetime(2026, 6, 9), None))

    with pytest.raises(TallyNotNumbered):
        allocate_ghabz_number(cursor, 42)
