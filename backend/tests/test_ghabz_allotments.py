"""The allotment maths must agree with TRG_CHK_GHABZ_TALI_LIMIT.

The trigger is the authority on what the database will accept. If these
expectations and the trigger ever disagree, the UI offers quantities that the
insert then rejects, so the rules are pinned here rather than left implicit.
"""

import pytest
from fastapi import HTTPException

from app.services.ghabz_allotment import (
    GhabzLineInput,
    annotate,
    available,
    drawable,
    full_draw,
    has_allotment,
    master_lines,
    over_issued,
    plan_lines,
    remaining,
    shared_anbar,
)


def allotment(**overrides):
    row = {
        "code_kala": 110,
        "description_kala": "گردو با پوست",
        "hscode": "08023100",
        "type_bastem": "کیسه",
        "id_anbar": 1,
        "id_tagh_anbar": 3,
        "number_hamel": "62ع971-36",
        "tally_line_count": 1,
        "tally_number_kala": 880,
        "tally_weighte": 22176,
        "tally_weighte_baskol": 21899,
        "issued_number_kala": 0,
        "issued_weighte_asnad": 0,
        "issued_weighte_baskol": 0,
    }
    row.update(overrides)
    return row


def test_remaining_is_allotment_minus_issued():
    row = allotment(issued_number_kala=300, issued_weighte_asnad=7000)

    assert remaining(row, "number_kala") == 580
    assert remaining(row, "weighte_asnad") == 15176
    assert remaining(row, "weighte_baskol") == 21899


def test_a_code_with_no_tally_quantity_is_notdrawable():
    """This is the ORA-20011 case: the trigger rejects an all-zero allotment."""
    row = allotment(tally_number_kala=0, tally_weighte=0, tally_weighte_baskol=0)

    assert not has_allotment(row)
    assert not drawable(row)


def test_a_null_code_is_neverdrawable():
    """NULL code_kala matches nothing in the trigger and collides on the UNIQUE."""
    assert not drawable(allotment(code_kala=None))


def test_a_fully_issued_code_is_notdrawable():
    row = allotment(
        issued_number_kala=880,
        issued_weighte_asnad=22176,
        issued_weighte_baskol=21899,
    )

    assert not drawable(row)


def test_default_draw_takes_exactly_what_remains():
    row = allotment(issued_number_kala=480, issued_weighte_asnad=12000)

    lines = plan_lines(None, [row], {110: row})

    assert len(lines) == 1
    assert lines[0]["number_kala"] == 400
    assert lines[0]["weighte_asnad"] == 10176
    assert lines[0]["weighte_baskol"] == 21899


def test_default_draw_skips_codes_with_nothing_left():
    empty = allotment(code_kala=99, issued_number_kala=880,
                      issued_weighte_asnad=22176, issued_weighte_baskol=21899)
    open_row = allotment(code_kala=110)

    lines = plan_lines(None, [empty, open_row], {99: empty, 110: open_row})

    assert [line["code_kala"] for line in lines] == [110]


def test_nothing_left_at_all_is_a_clear_refusal():
    row = allotment(issued_number_kala=880, issued_weighte_asnad=22176,
                    issued_weighte_baskol=21899)

    with pytest.raises(HTTPException) as caught:
        plan_lines(None, [row], {110: row})
    assert caught.value.status_code == 400
    assert "باقی‌مانده" in caught.value.detail


def test_partial_draw_is_allowed():
    row = allotment()
    request = [GhabzLineInput(code_kala=110, number_kala=400, weighte_asnad=10000)]

    lines = plan_lines(request, [row], {110: row})

    assert lines[0]["number_kala"] == 400
    assert lines[0]["weighte_asnad"] == 10000
    # an omitted measure still defaults to the full remainder
    assert lines[0]["weighte_baskol"] == 21899


def test_overdrawing_names_the_code_and_the_remainder():
    row = allotment(issued_number_kala=500)
    request = [GhabzLineInput(code_kala=110, number_kala=400)]

    with pytest.raises(HTTPException) as caught:
        plan_lines(request, [row], {110: row})
    assert caught.value.status_code == 400
    assert "380" in caught.value.detail
    assert "110" in caught.value.detail


def test_unknown_code_is_rejected_before_the_trigger_sees_it():
    row = allotment()

    with pytest.raises(HTTPException) as caught:
        plan_lines([GhabzLineInput(code_kala=777)], [row], {110: row})
    assert "777" in caught.value.detail


def test_duplicate_code_is_rejected_before_the_unique_constraint():
    row = allotment()
    request = [GhabzLineInput(code_kala=110), GhabzLineInput(code_kala=110)]

    with pytest.raises(HTTPException) as caught:
        plan_lines(request, [row], {110: row})
    assert "بیش از یک بار" in caught.value.detail


def test_negative_quantity_is_rejected():
    row = allotment()

    with pytest.raises(HTTPException):
        plan_lines([GhabzLineInput(code_kala=110, number_kala=-1)], [row], {110: row})


def test_a_line_drawing_nothing_is_rejected():
    row = allotment()
    request = [
        GhabzLineInput(code_kala=110, number_kala=0, weighte_asnad=0, weighte_baskol=0)
    ]

    with pytest.raises(HTTPException) as caught:
        plan_lines(request, [row], {110: row})
    assert "هیچ مقداری" in caught.value.detail


def test_full_draw_carries_the_descriptive_columns():
    line = full_draw(allotment())

    assert line["hscode"] == "08023100"
    assert line["type_basteh"] == "کیسه"
    assert line["id_tagh_anbar"] == 3


@pytest.mark.parametrize(
    "rows,expected",
    [
        ([{"id_anbar": 1}, {"id_anbar": 1}], 1),
        ([{"id_anbar": 1}, {"id_anbar": 2}], None),
        ([{"id_anbar": None}], None),
    ],
)
def test_header_warehouse_only_when_the_lines_agree(rows, expected):
    assert shared_anbar(rows) == expected


# --- over-issued rows -------------------------------------------------------
# A tally row deleted after receipts were issued against it leaves the receipts
# holding more than the tally now allots. The figures must never go negative on
# their way to an input, but the condition must still be visible.

def over_issued_row():
    return allotment(
        tally_weighte_baskol=1_000,
        issued_weighte_baskol=46_203_313,
        issued_number_kala=873,
        issued_weighte_asnad=20_378,
    )


def test_raw_remaining_stays_negative_so_the_condition_is_visible():
    assert remaining(over_issued_row(), "weighte_baskol") < 0


def test_available_never_goes_below_zero():
    assert available(over_issued_row(), "weighte_baskol") == 0


def test_over_issued_is_flagged():
    assert over_issued(over_issued_row())
    assert not over_issued(allotment())


def test_annotate_publishes_clamped_figures():
    rows = annotate([over_issued_row()])

    assert rows[0]["remaining_weighte_baskol"] == 0
    assert rows[0]["over_issued"] is True
    assert rows[0]["remaining_number_kala"] == 7


def test_an_over_issued_code_is_still_drawable_on_its_other_measures():
    """Code 24 in the report: baskol is overdrawn but 7 units remain."""
    assert drawable(over_issued_row())


def test_default_draw_on_an_over_issued_row_is_zero_not_negative():
    row = over_issued_row()

    lines = plan_lines(None, [row], {110: row})

    assert lines[0]["weighte_baskol"] == 0
    assert lines[0]["number_kala"] == 7


def test_drawing_on_an_exhausted_measure_is_refused_with_zero_as_the_limit():
    row = over_issued_row()

    with pytest.raises(HTTPException) as caught:
        plan_lines([GhabzLineInput(code_kala=110, weighte_baskol=5)], [row], {110: row})
    assert "0" in caught.value.detail


# --- app query / trigger coupling -------------------------------------------
# ALLOTMENTS_SQL and TRG_CHK_GHABZ_TALI_LIMIT compute the same sums and must
# agree on which rows count. When they drifted apart, deleting a receipt freed
# nothing in the UI. The router is read as text because importing it opens the
# Oracle connection pool.

import pathlib
import re

ROUTER = pathlib.Path(__file__).resolve().parents[1] / "app" / "routers" / "ghabz.py"


def issued_subqueries() -> list[str]:
    sql = re.search(r'ALLOTMENTS_SQL = """(.*?)"""', ROUTER.read_text(encoding="utf-8"), re.S)
    assert sql, "ALLOTMENTS_SQL not found"
    return re.findall(r"NVL\(\(\s*SELECT SUM\(d\.(.*?)\), 0\)", sql.group(1), re.S)


def test_all_three_issued_sums_are_present():
    assert len(issued_subqueries()) == 3


@pytest.mark.parametrize("index", [0, 1, 2])
def test_issued_sums_ignore_soft_deleted_receipt_lines(index):
    """A deleted line must release its quantity back to the tally."""
    assert "d.\"IS_DELETED\" = 'no'" in issued_subqueries()[index]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_issued_sums_ignore_soft_deleted_receipt_headers(index):
    """Deleting a whole receipt must release it too, even if its lines are live."""
    assert "h.\"IS_DELETED\" = 'no'" in issued_subqueries()[index]


def test_tally_allotment_ignores_soft_deleted_tally_rows():
    sql = re.search(
        r'ALLOTMENTS_SQL = """(.*?)"""', ROUTER.read_text(encoding="utf-8"), re.S
    ).group(1)
    inline_view = sql.split("FROM (", 1)[1]
    assert "t.\"IS_DELETED\" = 'no'" in inline_view


# --- master receipts --------------------------------------------------------
# A master (قبض انبار مادر) summarises the whole tally for internal records while
# child receipts split the same goods for customers. The amended trigger measures
# it on its own, so it carries full quantities regardless of what children took.

def test_master_takes_the_tally_total_not_the_remainder():
    row = allotment(issued_number_kala=600, issued_weighte_asnad=15_000)

    lines = master_lines([row])

    assert lines[0]["number_kala"] == 880
    assert lines[0]["weighte_asnad"] == 22176
    assert lines[0]["weighte_baskol"] == 21899


def test_master_covers_every_code_including_fully_issued_ones():
    spent = allotment(code_kala=99, issued_number_kala=880,
                      issued_weighte_asnad=22176, issued_weighte_baskol=21899)
    open_row = allotment(code_kala=110)

    lines = master_lines([spent, open_row])

    assert sorted(line["code_kala"] for line in lines) == [99, 110]


def test_master_skips_codes_the_trigger_would_reject():
    """NULL code and all-zero allotment both raise inside the trigger."""
    null_code = allotment(code_kala=None)
    zeroed = allotment(code_kala=77, tally_number_kala=0, tally_weighte=0,
                       tally_weighte_baskol=0)
    good = allotment(code_kala=110)

    lines = master_lines([null_code, zeroed, good])

    assert [line["code_kala"] for line in lines] == [110]


def test_master_on_an_empty_tally_is_refused():
    with pytest.raises(HTTPException) as caught:
        master_lines([allotment(code_kala=None)])
    assert caught.value.status_code == 400


def test_master_carries_the_descriptive_columns():
    line = master_lines([allotment()])[0]

    assert line["hscode"] == "08023100"
    assert line["type_basteh"] == "کیسه"


def test_issued_sums_exclude_master_receipts():
    """Otherwise a master would consume the allotment its children draw from."""
    for subquery in issued_subqueries():
        assert "IS_MASTER" in subquery
