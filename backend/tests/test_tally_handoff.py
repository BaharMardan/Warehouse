"""Operator / warehouse-keeper handoff rules. Pure Python: no Oracle connection."""

import pytest

from app.services import tally_handoff as rules


def test_operator_can_send_once_goods_rows_exist():
    assert rules.send_to_keeper_error("operator", goods_rows=1) is None
    assert rules.send_to_keeper_error("operator", goods_rows=0) == "ابتدا دست‌کم یک ردیف کالا ثبت کنید"


@pytest.mark.parametrize("step", ["keeper", "returned"])
def test_a_tally_is_sent_to_the_keeper_only_once(step):
    assert rules.send_to_keeper_error(step, goods_rows=5) is not None


def test_keeper_can_answer_no_without_pallets():
    assert rules.volumetric_error("keeper", "no", None) is None


def test_keeper_can_answer_yes_before_typing_pallets():
    assert rules.volumetric_error("keeper", "yes", None) is None
    assert rules.volumetric_error("keeper", "yes", 12) is None


@pytest.mark.parametrize("pallets", [0, -3, rules.MAX_PALLETS + 1])
def test_pallet_count_must_be_a_positive_whole_number(pallets):
    assert rules.volumetric_error("keeper", "yes", pallets) == "تعداد پالت باید عددی صحیح و دست‌کم ۱ باشد"


def test_no_never_carries_a_pallet_count():
    assert rules.volumetric_error("keeper", "no", 4) is not None


@pytest.mark.parametrize("step", ["operator", "returned"])
def test_the_answer_changes_only_while_the_keeper_holds_the_tally(step):
    assert rules.volumetric_error(step, "no", None) is not None


def test_returning_needs_an_answer():
    assert rules.return_to_operator_error("keeper", None, None) == "ابتدا به پرسش «آیا کالا حجمی است؟» پاسخ دهید"


def test_returning_volumetric_cargo_needs_pallets():
    assert rules.return_to_operator_error("keeper", "yes", None) == "برای کالای حجمی تعداد پالت را وارد کنید"
    assert rules.return_to_operator_error("keeper", "yes", 8) is None
    assert rules.return_to_operator_error("keeper", "no", None) is None


@pytest.mark.parametrize("step", ["operator", "returned"])
def test_only_a_tally_with_the_keeper_can_be_returned(step):
    assert rules.return_to_operator_error(step, "no", None) is not None


@pytest.mark.parametrize(("step", "allowed"), [("operator", False), ("keeper", False), ("returned", True), (None, False)])
def test_receipts_need_a_returned_tally(step, allowed):
    assert (rules.issue_receipt_error(step) is None) == allowed
