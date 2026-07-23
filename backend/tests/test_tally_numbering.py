from datetime import date

import oracledb

from app.services.tally_numbering import (
    allocate_next_tally_number,
    format_tally_number,
    jalali_year_for,
)


class _OracleUniqueError:
    code = 1


class _FakeVar:
    def __init__(self):
        self.value = None

    def getvalue(self):
        return self.value


class _FakeCounterCursor:
    def __init__(self):
        self.counters: dict[int, int] = {}
        self.rowcount = 0

    def var(self, _type):
        return _FakeVar()

    def execute(self, sql, params):
        year = params["jalali_year"]
        if sql.lstrip().startswith("INSERT"):
            if year in self.counters:
                raise oracledb.IntegrityError(_OracleUniqueError())
            self.counters[year] = 0
            self.rowcount = 1
            return

        self.counters[year] += 1
        params["next_number"].value = [self.counters[year]]
        self.rowcount = 1


def test_jalali_year_for_first_day_of_1405():
    assert jalali_year_for(date(2026, 3, 21)) == 1405


def test_jalali_year_resets_at_nowruz():
    assert jalali_year_for(date(2026, 3, 20)) == 1404
    assert jalali_year_for(date(2026, 3, 21)) == 1405


def test_format_tally_number():
    assert format_tally_number(1405, 1) == "1405-1"
    assert format_tally_number(1405, 2) == "1405-2"


def test_allocator_starts_at_one_and_increments_for_the_same_year():
    cursor = _FakeCounterCursor()

    assert allocate_next_tally_number(cursor, 1405) == "1405-1"
    assert allocate_next_tally_number(cursor, 1405) == "1405-2"


def test_allocator_restarts_for_a_new_year():
    cursor = _FakeCounterCursor()

    assert allocate_next_tally_number(cursor, 1405) == "1405-1"
    assert allocate_next_tally_number(cursor, 1406) == "1406-1"
