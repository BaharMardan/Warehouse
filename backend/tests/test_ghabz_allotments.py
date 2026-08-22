"""The allotment maths must agree with TRG_CHK_GHABZ_TALI_LIMIT.

The trigger is the authority on what the database will accept. If these
expectations and the trigger ever disagree, the UI offers quantities that the
insert then rejects, so the rules are pinned here rather than left implicit.
"""

import pytest
from fastapi import HTTPException

from app.services.ghabz_allotment import (
    GhabzLineInput,
    drawable,
    full_draw,
    has_allotment,
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
