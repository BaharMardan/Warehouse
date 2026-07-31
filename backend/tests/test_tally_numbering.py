import pytest

from app.services.tally_numbering import GLOBAL_COUNTER_KEY, allocate_next_tally_number


class _FakeVar:
    def __init__(self):
        self.value = None

    def getvalue(self):
        return self.value


class _FakeCounterCursor:
    def __init__(self, last_number: int | None):
        self.last_number = last_number
        self.rowcount = 0

    def var(self, _type):
        return _FakeVar()

    def execute(self, _sql, params):
        assert params["counter_key"] == GLOBAL_COUNTER_KEY
        if self.last_number is None:
            self.rowcount = 0
            return

        self.last_number += 1
        params["next_number"].value = [self.last_number]
        self.rowcount = 1


def test_allocator_continues_after_the_last_real_number():
    cursor = _FakeCounterCursor(1073)

    assert allocate_next_tally_number(cursor) == "1074"
    assert allocate_next_tally_number(cursor) == "1075"


def test_allocator_does_not_embed_or_depend_on_a_year():
    cursor = _FakeCounterCursor(1405)

    assert allocate_next_tally_number(cursor) == "1406"


def test_allocator_requires_go_live_initialization():
    cursor = _FakeCounterCursor(None)

    with pytest.raises(RuntimeError, match="not initialized"):
        allocate_next_tally_number(cursor)
