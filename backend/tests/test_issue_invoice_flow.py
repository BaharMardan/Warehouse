"""issue_invoice wiring with the database mocked by SQL text: cargo, days,
storage, pool share, settings and the prepayment/discount question."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routers import receipt_workflow as api
from app.services import receipt_db
from app.services.receipt_invoice import SERVICE_LABELS
from app.services.jalali import from_jalali


def receipt(is_master="no"):
    return {"id": 1, "tally_id": 10, "number_text": "1405_1503_2", "is_master": is_master,
            "status": "finalized",
            "requires_invoice": "yes", "line_count": 1, "allocation_ratio": Decimal("0.3"),
            "pallet_quantity": None}


TALLY = {"is_volumetric": "weight", "volumetric_pallets": None, "id_product_ownear": 5,
         "date_unloading": datetime.combine(from_jalali(1405, 1, 1), datetime.min.time())}
LINE = {"id": 1, "hscode": "7208", "description": "ورق", "goods_group": 1, "kala_code": "101",
        "storage_price": 56003, "zarib_mahal": "انبارداری مسقف", "number_hamel": None,
        "quantity": Decimal(3), "weight_kg": Decimal(30000)}


@pytest.fixture
def wired(monkeypatch):
    state = {"deductions": {"prepayment": 200000, "discount": 50000, "applied_rows": 0},
             "current": receipt(),
             # insured, ceiling 5,000,000,000; this receipt's customs value is covered
             "headers": [{"id_tali": 10, "is_bimeh": "بله", "number_bimeh": "B-1",
                          "sabt_sefaresh_number": "S-1"}],
             "totals": [{"id_tali": 10, "customs_value": 1_000_000_000,
                         "insured_ceiling": 5_000_000_000}],
             "receipt_values": [{"receipt_id": 1, "customs_value": 300_000_000}]}
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.var.return_value.getvalue.return_value = [555]
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    monkeypatch.setattr(receipt_db, "receipt",
                        lambda *a, **k: (state["current"], [state["current"]], TALLY))

    def one(_cur, sql, params=None):
        if sql == api.TEHRAN_TODAY_SQL:
            return {"today": datetime.combine(from_jalali(1405, 2, 1), datetime.min.time())}
        if sql == api.DEDUCTIONS_SQL:
            return state["deductions"]
        if '"ALLOCATION_RATIO") AS ratio' in sql:
            return {"ratio": None}
        return None   # no prior invoice, no buyer details

    def rows(_cur, sql, params=None):
        if sql == api.RECEIPT_STORAGE_SQL:
            return [LINE]
        if sql == api.INSURANCE_HEADERS_SQL:
            return state["headers"]
        if sql == api.INSURANCE_TOTALS_SQL:
            return state["totals"]
        if sql == api.RECEIPT_CUSTOMS_SQL:
            return state["receipt_values"]
        if sql == api.MISSING_CUSTOMS_SQL:
            return state.get("missing", [])
        if sql == api.INVOICE_SETTINGS_SQL:
            return [{"setting_key": "tax_rate", "value_number": 10},
                    {"setting_key": "system_service_rate", "value_number": 100000}]
        if '"FA_RECEIPT_SERVICE_POOL"' in sql:
            return [{"line_no": 0, "description": "snapshot", "price": 0},
                    {"line_no": 1, "description": SERVICE_LABELS["diamound"], "price": 1000000}]
        return []

    monkeypatch.setattr(receipt_db, "one", one)
    monkeypatch.setattr(receipt_db, "rows", rows)
    return state, conn, cur


def saved_rows(cur):
    (_, params), _ = cur.executemany.call_args
    return params


def test_detailed_receipt_must_answer_the_deduction_question(wired):
    _, conn, cur = wired
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1})
    assert exc.value.status_code == 422
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_yes_applies_prepayment_and_discount_on_this_invoice(wired):
    _, conn, cur = wired
    result = api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=True))
    assert result == {"invoice_id": 555}
    rows = saved_rows(cur)
    assert [r["kind"] for r in rows] == ["system", "storage", "service", "tax", "prepayment", "discount"]
    # 31 days with Farvardin 31 inside -> 30 days; 30 t at مسقف
    assert rows[1]["price"] == Decimal(75604050)          # 56,003 x 1.5 x 30 t x 30
    assert rows[2]["price"] == Decimal(300000)            # 30% of the frozen 1,000,000
    subtotal = Decimal(100000 + 75604050 + 300000)
    assert rows[3]["price"] == Decimal(7600405)           # 10% of 76,004,050
    assert [r["price"] for r in rows[4:]] == [-200000, -50000]
    assert all("اعمال‌شده روی قبض \u20661405_1503_2\u2069" in r["note"] for r in rows[4:])
    assert sum(r["price"] for r in rows) == subtotal + Decimal(7600405) - 250000
    header_params = cur.execute.call_args_list[0].args[1]
    assert header_params["calc_note"].startswith("نوع بار: وزنی؛ 1405/01/01 تا 1405/02/01")
    conn.commit.assert_called_once()


def test_no_leaves_deductions_for_another_receipt(wired):
    _, _, cur = wired
    api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False))
    assert [r["kind"] for r in saved_rows(cur)] == ["system", "storage", "service", "tax"]


def test_general_receipt_applies_deductions_without_asking(wired):
    state, _, cur = wired
    state["current"] = {**receipt("yes"), "allocation_ratio": Decimal(1)}
    api.issue_invoice(1, {"id": 1})
    assert [r["kind"] for r in saved_rows(cur)][-2:] == ["prepayment", "discount"]


def test_deductions_already_applied_are_not_asked_again(wired):
    state, _, cur = wired
    state["deductions"] = {**state["deductions"], "applied_rows": 2}
    api.issue_invoice(1, {"id": 1})
    assert "prepayment" not in [r["kind"] for r in saved_rows(cur)]


def test_missing_unloading_date_is_refused(wired, monkeypatch):
    monkeypatch.setattr(receipt_db, "receipt",
                        lambda *a, **k: (receipt(), [receipt()], {**TALLY, "date_unloading": None}))
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=True))
    assert exc.value.status_code == 409


def test_insurance_shortfall_after_an_earlier_tally(wired):
    state, _, cur = wired
    # tally 9 was registered first and used 4,800,000,000 of the 5,000,000,000 ceiling
    state["headers"] = [{**state["headers"][0], "id_tali": 9}, state["headers"][0]]
    state["totals"] = [{"id_tali": 9, "customs_value": 4_800_000_000, "insured_ceiling": 5_000_000_000},
                       state["totals"][0]]
    api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False))
    rows = saved_rows(cur)
    assert [r["kind"] for r in rows] == ["system", "storage", "service", "insurance", "tax"]
    # this receipt: 300,000,000 of value, 200,000,000 cover left -> 100,000,000 x 0.00055 x 30
    assert rows[3]["price"] == Decimal(1650000)
    assert "مصرف تالی‌های قبلی 4,800,000,000" in rows[3]["note"]


def test_uninsured_tally_is_charged_on_the_receipts_customs_value(wired):
    state, _, cur = wired
    state["headers"] = [{**state["headers"][0], "is_bimeh": "خیر"}]
    api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False))
    insurance = [r for r in saved_rows(cur) if r["kind"] == "insurance"]
    assert insurance[0]["price"] == Decimal(4950000)   # 300,000,000 x 0.00055 x 30


def test_missing_customs_needs_confirmation_with_a_clear_error(wired):
    state, conn, cur = wired
    state["missing"] = [{"id": 1, "hscode": "7208", "description": "ورق"}]
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False))
    assert exc.value.status_code == 422
    assert "ارزش گمرکی ردیف‌های 7208 در تالی ثبت نشده است" in exc.value.detail
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_confirmed_missing_customs_issues_with_a_zero_insurance_row(wired):
    state, _, cur = wired
    state["missing"] = [{"id": 1, "hscode": "7208", "description": "ورق"}]
    state["receipt_values"] = [{"receipt_id": 1, "customs_value": 0}]
    api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False,
                                                           confirm_missing_customs=True))
    insurance = [r for r in saved_rows(cur) if r["kind"] == "insurance"]
    assert insurance[0]["price"] == 0 and "(ردیف‌ها: 7208)" in insurance[0]["note"]
