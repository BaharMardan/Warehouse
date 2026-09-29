from datetime import date, datetime
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.services import receipt_db as db
from app.routers import receipt_workflow as api
from app.crud.registry import TaliHeaderInput
from app.services.jalali import from_jalali
from test_issue_invoice_flow import wired, saved_rows


@pytest.mark.parametrize("exit_day,billed", [(from_jalali(1405, 3, 1), 60),
                                           (from_jalali(1405, 1, 15), 30)])
def test_invoice_uses_exit_date_even_if_after_issue_day(wired, exit_day, billed, monkeypatch):
    state, conn, cur = wired
    original = db.receipt
    def receipt(*args, **kwargs):
        current, siblings, tally = original(*args, **kwargs)
        return current, siblings, {**tally, "date_cargo_exit": exit_day}
    monkeypatch.setattr(db, "receipt", receipt)
    api.issue_invoice(1, {"id": 1}, api.InvoiceIssueInput(apply_deductions=False))
    storage = next(row for row in saved_rows(cur) if row["kind"] == "storage")
    assert storage["price"] == 56003 * 1.5 * 30 * billed
    conn.commit.assert_called_once()


def test_invoice_rejects_exit_before_unloading(wired, monkeypatch):
    _, conn, _ = wired
    original = db.receipt
    def receipt(*args, **kwargs):
        current, siblings, tally = original(*args, **kwargs)
        return current, siblings, {**tally, "date_cargo_exit": date(2020, 1, 1)}
    monkeypatch.setattr(db, "receipt", receipt)
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1})
    assert exc.value.status_code == 422
    conn.commit.assert_not_called()


@pytest.mark.parametrize("status", ["created", "finalized", "invoice_issued"])
def test_header_update_remains_open_but_delete_and_goods_stay_guarded(monkeypatch, status):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.rowcount = 1
    monkeypatch.setattr(db, "get_connection", lambda: conn)
    monkeypatch.setattr(db, "one", lambda *a: {"id_headers_tali": 1})
    lock = MagicMock(return_value={"date_unloading": datetime(2026, 1, 1)})
    monkeypatch.setattr(db, "lock_tally", lock)
    monkeypatch.setattr(db, "receipts", lambda *a: [{"status": status}])
    assert db.guarded_write("FA_TALI_HEADER", "ID_TALI", "update", "UPDATE header",
                            {}, row_id=1, values={"discount": 100}) == 1
    lock.assert_called_once_with(cur, 1)
    conn.commit.assert_called_once()
    for table, action in [("FA_TALI_HEADER", "delete"), ("FA_TALI_DETAILES", "update")]:
        with pytest.raises(HTTPException) as exc:
            db.guarded_write(table, "ID", action, "mutation", {}, row_id=1)
        assert exc.value.status_code == 409


def test_partial_header_updates_validate_against_saved_dates(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(db, "get_connection", lambda: conn)
    monkeypatch.setattr(db, "one", lambda *a: {})
    monkeypatch.setattr(db, "lock_tally", lambda *a: {
        "date_unloading": datetime(2026, 1, 1), "date_cargo_exit": datetime(2026, 2, 1)})
    with pytest.raises(HTTPException):
        db.guarded_write("FA_TALI_HEADER", "ID_TALI", "update", "mutation", {},
                         row_id=1, values={"date_unloading": "2026-03-01"})
    conn.commit.assert_not_called()


def test_optional_exit_date_can_be_cleared_and_invalid_dates_rejected():
    assert TaliHeaderInput().date_cargo_exit is None
    assert TaliHeaderInput(date_cargo_exit="2026-10-01").date_cargo_exit == date(2026, 10, 1)
    assert TaliHeaderInput(date_cargo_exit=None).model_dump(exclude_unset=True) == {"date_cargo_exit": None}
    with pytest.raises(ValidationError):
        TaliHeaderInput(date_cargo_exit="2026-02-30")
    db.validate_header_dates({"date_unloading": "2026-03-01", "date_cargo_exit": None})
