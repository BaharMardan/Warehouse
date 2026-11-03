"""Invoice preview is read-only; final issue requires its current quote and a manual number."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import oracledb
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers import receipt_workflow as api
from app.services import receipt_db as db
from test_issue_invoice_flow import wired, saved_rows


def preview_payload(**changes):
    return api.InvoiceIssueInput(apply_deductions=False, **changes)


def final_payload(preview, number=555):
    return preview_payload(invoice_number=number, preview_hash=preview["preview_hash"])


def test_preview_returns_current_payable_without_writes(wired):
    _, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    assert Decimal(result["totals"]["payable"]) == sum(Decimal(row["price"]) for row in result["rows"])
    assert result["totals"]["total_with_tax"] == result["totals"]["payable"]
    assert len(result["preview_hash"]) == 64
    cur.execute.assert_not_called()
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_preview_and_issue_have_identical_rows_and_manual_number(wired):
    _, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    assert api.issue_invoice(1, {"id": 1}, final_payload(result)) == {"invoice_id": 555}
    assert [str(row["price"]) for row in saved_rows(cur)] == [row["price"] for row in result["rows"]]
    sql, params = cur.execute.call_args_list[0].args
    assert '"ID_SORAT"' in sql and ":invoice_number" in sql
    assert params["invoice_number"] == 555
    conn.commit.assert_called_once()


def test_number_is_required_even_with_a_valid_preview(wired):
    _, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, preview_payload(preview_hash=result["preview_hash"]))
    assert exc.value.status_code == 422
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "", "12.5", "1e3", "12/3", 10**15])
def test_invalid_manual_numbers_are_rejected(value):
    with pytest.raises(ValidationError):
        api.InvoiceIssueInput(invoice_number=value)


@pytest.mark.parametrize("value", ["555", "۵۵۵", "٥٥٥"])
def test_manual_number_accepts_latin_persian_and_arabic_digits(value):
    assert api.InvoiceIssueInput(invoice_number=value).invoice_number == 555


def test_stale_amount_does_not_issue(wired):
    state, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    state["headers"] = [{**state["headers"][0], "is_bimeh": "خیر"}]
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, final_payload(result))
    assert exc.value.status_code == 409
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_issue_requires_a_preview(wired):
    _, conn, cur = wired
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, preview_payload(invoice_number=555))
    assert exc.value.status_code == 409
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_active_duplicate_number_cannot_issue(wired, monkeypatch):
    _, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    original = db.one
    def one(cursor, sql, params=None):
        if params and "invoice_number" in params:
            assert "SORAT_IS_DELETED" in sql
            assert "INVOICE_NUMBER" in sql
            return {"id": 555}
        return original(cursor, sql, params)
    monkeypatch.setattr(db, "one", one)
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, final_payload(result))
    assert exc.value.status_code == 409
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_concurrent_duplicate_is_a_clear_conflict(wired):
    _, conn, cur = wired
    result = api.preview_invoice(1, preview_payload())
    cur.execute.side_effect = oracledb.IntegrityError(SimpleNamespace(code=1))
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1}, final_payload(result))
    assert exc.value.status_code == 409
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_volumetric_preview_resolves_pallets_without_persisting(wired, monkeypatch):
    state, conn, cur = wired
    state["current"]["pallet_quantity"] = 5
    original = db.receipt
    def receipt(*args, **kwargs):
        current, siblings, tally = original(*args, **kwargs)
        return current, siblings, {**tally, "is_volumetric": "volumetric"}
    monkeypatch.setattr(db, "receipt", receipt)
    monkeypatch.setattr(api.rp, "tally_rows", lambda *args: [{"id": 1, "pallets": 5}])
    monkeypatch.setattr(api.rp, "receipt_rows", lambda *args: [{"id": 1, "pallets": 5}])
    monkeypatch.setattr(api, "source_rows", lambda *args: [])
    monkeypatch.setattr(api.rp, "allocations", lambda *args: [])
    monkeypatch.setattr(api.rp, "resolve_counts", lambda *args: {1: 5})
    persist = MagicMock()
    monkeypatch.setattr(api.rp, "ensure_receipt_counts", persist)
    result = api.preview_invoice(1, preview_payload())
    assert any(row["kind"] == "storage" for row in result["rows"])
    persist.assert_not_called()
    cur.executemany.assert_not_called()
    conn.commit.assert_not_called()


def test_pallets_are_saved_only_on_final_issue(wired, monkeypatch):
    state, conn, cur = wired
    state["current"]["pallet_quantity"] = 5
    original = db.receipt
    def receipt(*args, **kwargs):
        current, siblings, tally = original(*args, **kwargs)
        return current, siblings, {**tally, "is_volumetric": "volumetric"}
    monkeypatch.setattr(db, "receipt", receipt)
    monkeypatch.setattr(api.rp, "tally_rows", lambda *args: [{"id": 1, "pallets": 5}])
    monkeypatch.setattr(api.rp, "receipt_rows", lambda *args: [{"id": 1, "pallets": 5}])
    monkeypatch.setattr(api, "source_rows", lambda *args: [{
        "id": 1, "quantity_share": 1, "weight_share": 1, "baskol_share": 1}])
    monkeypatch.setattr(api.rp, "allocations", lambda *args: [])
    monkeypatch.setattr(api.rp, "resolve_counts", lambda *args: {1: 5})
    persist = MagicMock()
    monkeypatch.setattr(api.rp, "ensure_receipt_counts", persist)
    result = api.preview_invoice(1, preview_payload())
    persist.assert_not_called()
    api.issue_invoice(1, {"id": 1}, final_payload(result))
    persist.assert_called_once()
    conn.commit.assert_called_once()
