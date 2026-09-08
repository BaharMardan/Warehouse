"""Sequence 0 is what makes one-master-per-tally free.

The master always takes GHABZ_SEQ = 0, so UQ_FA_GHABZ_TALI_SEQ rejects a second
one without any application check, and MAX(GHABZ_SEQ) + 1 still gives 1 to the
first child because 0 sorts below it. The 0 is stored, not printed: a number
without a sequence suffix identifies the master.
"""

from datetime import datetime

import pytest

from app.services.ghabz_numbering import (
    MASTER_SEQUENCE,
    MasterAlreadyIssued,
    allocate_ghabz_number,
    format_ghabz_number,
)


class _FakeCursor:
    def __init__(self, tally_row, highest_sequence=None, master_row=None,
                 now=datetime(2026, 8, 22)):
        self.tally_row = tally_row
        self.highest_sequence = highest_sequence
        self.master_row = master_row
        self.now = now
        self._result = None

    def execute(self, sql, params=None):
        if "FOR UPDATE" in sql:
            self._result = self.tally_row
        elif "SYSDATE" in sql:
            self._result = (self.now,)
        elif "GHABZ_SEQ" in sql and "MAX" not in sql:
            self._result = self.master_row
        elif "GHABZ_SEQ" in sql:
            self._result = ((self.highest_sequence or 0) + 1,)
        else:
            raise AssertionError(f"unexpected statement: {sql}")

    def fetchone(self):
        return self._result


def tally(number="1503"):
    return (number, datetime(2026, 6, 9), None)


def test_master_takes_sequence_zero():
    number, sequence, _ = allocate_ghabz_number(_FakeCursor(tally()), 1, is_master=True)

    assert sequence == MASTER_SEQUENCE == 0
    assert number == "1405_1503"


def test_first_child_is_one_even_though_a_master_holds_zero():
    cursor = _FakeCursor(tally(), highest_sequence=0)

    assert allocate_ghabz_number(cursor, 1)[0] == "1405_1503_1"


def test_children_continue_past_the_master():
    cursor = _FakeCursor(tally(), highest_sequence=6)

    assert allocate_ghabz_number(cursor, 1)[0] == "1405_1503_7"


def test_a_live_master_blocks_a_second_one():
    cursor = _FakeCursor(tally(), master_row=(637, "1405_1503", "no"))

    with pytest.raises(MasterAlreadyIssued):
        allocate_ghabz_number(cursor, 1, is_master=True)


def test_a_deleted_master_does_not_block_allocation():
    """The caller revives it instead; the master number stays with the original row."""
    cursor = _FakeCursor(tally(), master_row=(637, "1405_1503", "yes"))

    assert allocate_ghabz_number(cursor, 1, is_master=True)[1] == 0


def test_master_number_has_no_sequence_suffix():
    assert format_ghabz_number(1405, "1503", 0) == "1405_1503"


def test_child_numbers_keep_their_sequence_suffix():
    assert format_ghabz_number(1405, "1503", 1) == "1405_1503_1"
    assert format_ghabz_number(1405, "1503", 12) == "1405_1503_12"
