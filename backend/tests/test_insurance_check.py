"""The ceiling maths behind the /tally/{id}/insurance-check endpoint.

An insurance is identified by one aligned (NUMBER_BIMEH, SABT_SEFARESH_NUMBER)
line pair and several tallies may carry the same pair. INSURED_VALUE is the
policy's single ceiling repeated on the goods rows, so it is collapsed with
MAX and never summed; CUSTOMS_VALUE is summed across all of those tallies'
active rows. The rules are pinned here so the warning banner and the invoice
difference always agree.
"""

from decimal import Decimal

from app.services.insurance_check import (
    check_insurance_ceilings,
    normalize_number_text,
    parse_insurance_pairs,
)


def header(row_id, tali_number, bimeh, sabt):
    return {
        "id_tali": row_id,
        "tali_number": tali_number,
        "number_bimeh": bimeh,
        "sabt_sefaresh_number": sabt,
    }


def totals(customs, ceiling):
    return {"customs_value": customs, "insured_ceiling": ceiling}


def test_normalize_number_text_unifies_persian_and_arabic_digits():
    assert normalize_number_text(" ۱۲۳ ") == "123"
    assert normalize_number_text("٤٥٦") == "456"
    assert normalize_number_text(None) == ""


def test_parse_pairs_aligns_lines_and_pads_the_shorter_column():
    assert parse_insurance_pairs("111\n222", "901") == [("111", "901"), ("222", "")]


def test_parse_pairs_keeps_a_pair_whose_bimeh_line_is_empty():
    # Alignment is by line index, so a middle empty بیمه نامه line must not
    # shift the following pairs.
    assert parse_insurance_pairs("111\n\n333", "901\n902\n903") == [
        ("111", "901"),
        ("", "902"),
        ("333", "903"),
    ]


def test_parse_pairs_drops_fully_empty_lines_and_duplicates():
    assert parse_insurance_pairs("111\n\n111", "901\n\n901") == [("111", "901")]
    assert parse_insurance_pairs(None, None) == []


def test_customs_sums_across_tallies_but_the_ceiling_is_never_summed():
    # Both tallies of the policy repeat its ceiling (900); the check must use
    # 900, not 1800.
    headers = [
        header(1, "1504", "111", "901"),
        header(2, "1505", "111", "901"),
        header(3, "1506", "999", "901"),  # same ثبت سفارش, different بیمه نامه
    ]
    totals_by_header = {
        1: totals(600, 900),
        2: totals(500, 900),
        3: totals(10_000, 10_000),
    }

    [result] = check_insurance_ceilings(1, headers, totals_by_header)

    assert result["number_bimeh"] == "111"
    assert result["sabt_sefaresh_number"] == "901"
    assert result["total_customs_value"] == Decimal(1100)
    assert result["insured_ceiling"] == Decimal(900)
    assert result["overage"] == Decimal(200)
    assert result["is_over"] is True
    assert result["tally_numbers"] == ["1504", "1505"]


def test_within_the_ceiling_is_reported_but_not_flagged():
    headers = [header(1, "1504", "111", "901")]

    [result] = check_insurance_ceilings(1, headers, {1: totals(500, 500)})

    assert result["overage"] == Decimal(0)
    assert result["is_over"] is False


def test_inconsistent_repeated_ceilings_resolve_to_the_largest():
    # Data-entry variance across rows/tallies: the largest recorded policy
    # value wins, keeping the warning conservative.
    headers = [
        header(1, "1504", "111", "901"),
        header(2, "1505", "111", "901"),
    ]
    totals_by_header = {1: totals(600, 900), 2: totals(500, 1000)}

    [result] = check_insurance_ceilings(1, headers, totals_by_header)

    assert result["insured_ceiling"] == Decimal(1000)
    assert result["overage"] == Decimal(100)
    assert result["is_over"] is True


def test_no_recorded_ceiling_anywhere_yields_no_warning():
    headers = [header(1, "1504", "111", "901")]

    [result] = check_insurance_ceilings(1, headers, {1: totals(700, None)})

    assert result["insured_ceiling"] is None
    assert result["overage"] is None
    assert result["is_over"] is False


def test_pair_matching_uses_normalized_digits():
    # A legacy header saved with Persian digits still belongs to the same
    # insurance as one saved after the frontend normalization.
    headers = [
        header(1, "1504", "۱۱۱", "۹۰۱"),
        header(2, "1505", "111", "901"),
    ]
    totals_by_header = {1: totals(600, 900), 2: totals(500, 900)}

    [result] = check_insurance_ceilings(1, headers, totals_by_header)

    assert result["total_customs_value"] == Decimal(1100)
    assert result["is_over"] is True


def test_header_without_active_goods_rows_contributes_zero():
    headers = [
        header(1, "1504", "111", "901"),
        header(2, "1505", "111", "901"),  # no entry in totals_by_header
    ]

    [result] = check_insurance_ceilings(1, headers, {1: totals(300, 300)})

    assert result["total_customs_value"] == Decimal(300)
    assert result["tally_numbers"] == ["1504", "1505"]


def test_each_pair_of_a_multi_insurance_header_is_checked_independently():
    headers = [
        header(1, "1504", "111\n222", "901\n902"),
        header(2, "1505", "222", "902"),
    ]
    totals_by_header = {1: totals(100, 400), 2: totals(900, 400)}

    first, second = check_insurance_ceilings(1, headers, totals_by_header)

    assert (first["number_bimeh"], first["sabt_sefaresh_number"]) == ("111", "901")
    assert first["is_over"] is False
    assert (second["number_bimeh"], second["sabt_sefaresh_number"]) == ("222", "902")
    # 100 + 900 customs against the shared 400 ceiling.
    assert second["overage"] == Decimal(600)
    assert second["is_over"] is True


def test_unknown_or_pairless_header_yields_no_entries():
    headers = [header(1, "1504", None, None)]

    assert check_insurance_ceilings(1, headers, {}) == []
    assert check_insurance_ceilings(99, headers, {}) == []
