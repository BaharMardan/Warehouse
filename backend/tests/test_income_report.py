from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.routers import reports as api
from app.services import income_report as ir


@pytest.mark.parametrize("kind,description,expected", [
    ("system", "خدمات سیستمی", "system"),
    ("storage", "هزینه انبارداری کد کالای 101", "storage"),
    ("storage", "انبارداری باقی‌مانده — برنج (کد 110)", "storage"),
    ("insurance", "بیمه باقی‌مانده", "insurance"),
    ("tax", "مالیات بر ارزش افزوده", "tax"),
    ("discount", "تخفیف", "discount"),
    ("prepayment", "کسر پیش‌پرداخت", "prepayment"),
    ("service", "استریپ", "strip"),
    ("service", "تخلیه", "unloading"),
    ("service", "استریپ و تخلیه", "combined"),
    ("service", "تخلیه و استریپ", "combined"),
    ("service", "استافینگ", "stuffing"),
    ("service", "بارگیری", "loading"),
    ("service", "استافینگ و بارگیری", "combined"),
    ("service", "هزینه کل استریپ / تخلیه", "combined"),
    ("service", "هزینه کل استافینگ / بارگیری", "combined"),
    ("service", "هزینه جابه‌جایی کانتینر با جرثقیل — کانتینر20 فوت خالی ( هردستگاه)", "crane"),
    ("service", "هزینه باربری", "transportation"),
    ("service", "هزینه کل دیماند", "demurrage"),
    ("service", "هزینه کل حق ورودی (حق محوطه)", "vehicle_enter"),
    ("service", "هزینه کل توقف شبانه", "night_stop"),
    ("service", "هزینه کل سایر خدمات", "other_service"),
    ("service", "سایر خدمات — پلمپ (هرعدد) — تعداد 2", "other_service"),
    ("service", "چیز ناشناخته", "other_service"),
])
def test_rows_of_a_1405_invoice_are_classified_by_kind_and_description(kind, description, expected):
    assert ir.classify_row(kind, description) == expected


@pytest.mark.parametrize("description,expected", [
    ("هزینه کد کالای 101", "storage"),
    ("هزینه کل استریپ و استافینگ", "combined"),
    ("هزینه کل دیماند", "demurrage"),
    ("هزینه کل توقف شبانه", "night_stop"),
    ("هزینه", "other"),
    (None, "other"),
])
def test_legacy_rows_without_a_kind_are_recognised_by_their_description(description, expected):
    assert ir.classify_row(None, description) == expected


def line(invoice, kind, description, amount):
    return {"invoice_id": invoice, "row_kind": kind, "description": description, "amount": amount}


SAMPLE = [
    line(1, "system", "خدمات سیستمی", 1000),
    line(1, "storage", "هزینه انبارداری کد کالای 101", 10000),
    line(1, "service", "استریپ", 4000),
    line(1, "insurance", "هزینه بیمه", 0),
    line(1, "discount", "تخفیف", -500),
    line(1, "tax", "مالیات بر ارزش افزوده", 1450),
    line(1, "prepayment", "کسر پیش‌پرداخت", -2000),
    line(2, "storage", "هزینه انبارداری کد کالای 110", 5000),
    line(2, "service", "بارگیری", 3000),
    line(2, "tax", "مالیات بر ارزش افزوده", 800),
]


def by_key(result):
    return {c["key"]: c for c in result["categories"]}


def test_categories_add_up_to_the_invoice_totals():
    result = ir.summarize(SAMPLE)
    summary = result["summary"]

    assert summary["gross"] == 23000
    assert summary["discount"] == 500
    assert summary["net"] == 22500
    assert summary["tax"] == 2250
    assert summary["total_with_tax"] == 24750
    assert summary["prepayment"] == 2000
    assert summary["payable"] == 22750
    assert summary["payable"] == sum(row["amount"] for row in SAMPLE)
    assert result["invoice_count"] == 2


def test_each_category_is_reported_separately_with_its_own_count():
    categories = by_key(ir.summarize(SAMPLE))

    assert (categories["storage"]["amount"], categories["storage"]["invoices"]) == (15000, 2)
    assert categories["strip"]["amount"] == 4000
    assert categories["loading"]["amount"] == 3000
    assert categories["unloading"]["amount"] == 0
    assert categories["unloading"]["lines"] == 0


def test_every_category_is_always_listed_in_a_fixed_order():
    keys = [c["key"] for c in ir.summarize([])["categories"]]

    assert keys == [key for key, _, _ in ir.CATEGORIES]
    assert ir.summarize([])["summary"]["payable"] == 0


def test_old_combined_handling_rows_are_left_out_of_every_figure():
    rows = SAMPLE + [line(3, "service", "هزینه کل استریپ / تخلیه", 9000),
                     line(3, "service", "استافینگ و بارگیری", 700)]

    result = ir.summarize(rows)

    assert result["summary"]["gross"] == 23000           # unchanged: nothing of them is counted
    assert result["invoice_count"] == 2
    assert result["left_out"] == {"lines": 2, "amount": 9700}
    assert "combined" not in [c["key"] for c in result["categories"]]
    assert all(row["category"] != "combined" for row in ir.classified(rows))
    assert not any("توأم" in c["label"] for c in result["categories"])


def test_zero_amount_rows_are_not_counted_like_on_the_invoice_screens():
    categories = by_key(ir.summarize(SAMPLE))

    assert categories["insurance"]["lines"] == 0


def test_amounts_keep_exact_decimal_precision():
    result = ir.summarize([line(1, "storage", "انبارداری", 0.1), line(1, "storage", "انبارداری", 0.2)])

    assert by_key(result)["storage"]["amount"] == Decimal("0.3")


def test_prepayment_never_reduces_income_only_the_payable_balance():
    summary = ir.summarize([line(1, "storage", "انبارداری", 10000),
                            line(1, "tax", "مالیات", 900),
                            line(1, "prepayment", "کسر پیش‌پرداخت", -4000)])["summary"]

    assert summary["net"] == 10000 and summary["gross"] == 10000
    assert summary["total_with_tax"] == 10900
    assert summary["prepayment"] == 4000
    assert summary["payable"] == 6900


def test_supplementary_invoices_are_income_and_are_also_reported_apart():
    rows = [line(1, "storage", "انبارداری", 1000),
            {**line(2, "storage", "انبارداری باقی‌مانده — x", 300), "original_invoice_id": 1},
            {**line(2, "insurance", "بیمه باقی‌مانده", 50), "original_invoice_id": 1}]

    result = ir.summarize(rows)

    assert result["summary"]["net"] == 1350
    assert result["invoice_count"] == 2
    assert result["supplementary"] == {"invoices": 1, "amount": 350}


def test_cancelled_invoices_are_totalled_apart_from_income():
    result = ir.summarize_cancelled([
        {"invoice_id": 5, "amount": 1000, "reissued": 1},
        {"invoice_id": 6, "amount": "250.5", "reissued": 0}])

    assert result["count"] == 2 and result["amount"] == Decimal("1250.5")


def test_income_report_endpoint_serializes_totals(monkeypatch):
    monkeypatch.setattr(api, "income_rows", lambda period: SAMPLE)
    monkeypatch.setattr(api, "cancelled_rows", lambda period: [
        {"invoice_id": 9, "issued_at": None, "amount": 700, "reissued": 1}])

    result = api.income_summary((date(2026, 1, 1), date(2026, 1, 31)), {})

    assert result["from"] == "2026-01-01" and result["to"] == "2026-01-31"
    assert result["summary"]["payable"] == 22750
    assert isinstance(result["categories"][0]["amount"], int)
    assert result["cancelled"]["count"] == 1 and result["cancelled"]["amount"] == 700
    assert result["supplementary"] == {"invoices": 0, "amount": 0}


def test_lines_endpoint_filters_by_category_and_totals_what_it_returns(monkeypatch):
    monkeypatch.setattr(api, "income_rows", lambda period: SAMPLE)
    period = (date(2026, 1, 1), date(2026, 1, 31))

    result = api.income_lines(period, "storage", {})

    assert [row["amount"] for row in result["lines"]] == [10000, 5000]
    assert result["total"] == 15000
    assert {row["category_label"] for row in result["lines"]} == {"انبارداری"}
    assert len(api.income_lines(period, None, {})["lines"]) == 9


def test_lines_endpoint_rejects_an_unknown_category():
    with pytest.raises(HTTPException) as exc:
        api.income_lines((date(2026, 1, 1), date(2026, 1, 2)), "nope", {})

    assert exc.value.status_code == 422


def test_period_must_not_end_before_it_starts():
    with pytest.raises(HTTPException) as exc:
        api.report_period(date(2026, 2, 1), date(2026, 1, 1))

    assert exc.value.status_code == 422
    assert api.report_period(date(2026, 1, 1), date(2026, 1, 1)) == (date(2026, 1, 1), date(2026, 1, 1))


def test_income_query_covers_the_whole_last_day_and_skips_cancelled_invoices():
    assert 's."SORAT_CREATE_AT" < :end_before' in api.INCOME_ROWS_SQL
    assert 'NVL(s."SORAT_IS_DELETED", \'no\') = \'no\'' in api.INCOME_ROWS_SQL
    assert "NOT IN ('Y', 'yes')" in api.INCOME_ROWS_SQL
    assert 's."SORAT_IS_DELETED" = \'yes\'' in api.CANCELLED_SQL
    assert 's."SORAT_CREATE_AT" < :end_before' in api.CANCELLED_SQL
