from decimal import Decimal
import pytest
from fastapi import HTTPException
from app.services.non_customs import Amounts, validate_amounts, validate_bill
from app.services.remaining_invoice import RemainingBatchInput

def test_exit_cannot_exceed_any_stock_dimension():
    with pytest.raises(HTTPException):
        validate_amounts(Amounts(weight=2, quantity=11), {"weight": 10, "quantity": 10}, "weight")

def test_volumetric_requires_pallets():
    with pytest.raises(HTTPException):
        validate_amounts(Amounts(weight=2), {"weight": 10}, "volumetric")

def test_exact_remaining_exit_is_valid():
    assert validate_amounts(Amounts(weight=10, quantity=2), {"weight": 10, "quantity": 2}, "weight")["weight"] == Decimal(10)

def test_billing_repeated_source_cannot_bypass_stock_limit():
    payload = RemainingBatchInput(days=3, insurance_percent=0, rows=[
        {"source_id": 1, "hscode": "123", "kala_code": "100", "amount": 6},
        {"source_id": 1, "hscode": "123", "kala_code": "100", "amount": 6}])
    with pytest.raises(HTTPException):
        validate_bill(payload, [{"source_id": 1, "weight": 10}], "weight")

def test_billing_cannot_use_unregistered_row():
    payload = RemainingBatchInput(days=3, insurance_percent=0, rows=[
        {"source_id": 2, "hscode": "123", "kala_code": "100", "amount": 1}])
    with pytest.raises(HTTPException):
        validate_bill(payload, [{"source_id": 1, "weight": 10}], "weight")


from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, date
from app.routers import non_customs as api
from app.services.non_customs import Registration, Exit

@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    monkeypatch.setattr(api.db, "receipt", lambda *a, **k: ({}, [], {}))
    monkeypatch.setattr(api.db, "one", lambda *a, **k: None)
    return conn, cur

def test_registration_saves_only_billed_source_balance(wired, monkeypatch):
    conn, cur = wired
    monkeypatch.setattr(api.db, "rows", lambda *a, **k: [{"receipt_id": 7,
        "source_id": 9, "invoice_id": 30, "invoice_date": datetime(2026, 1, 1),
        "cargo": "weight", "weight": 100, "quantity": 20, "pallets": 0}])
    result = api.register(7, Registration(source_id=9, weight=40, quantity=8,
        start_date=date(2026, 1, 2), settlement_confirmed=True), {"id": 1})
    assert result == {"registered": True}
    assert cur.execute.call_args.args[1]["weight"] == 40
    conn.commit.assert_called_once()

def test_registration_requires_settlement_confirmation(wired):
    conn, cur = wired
    with pytest.raises(HTTPException):
        api.register(7, Registration(source_id=9, weight=40,
            start_date=date(2026, 1, 2), settlement_confirmed=False), {"id": 1})
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()

def test_overdrawn_exit_does_not_commit(wired, monkeypatch):
    conn, cur = wired
    monkeypatch.setattr(api, "stock", lambda *a: [{"source_id": 9, "cargo": "weight", "weight": 10}])
    with pytest.raises(HTTPException):
        api.record_exit(7, 9, Exit(weight=11, request_id=uuid4()), {"id": 1})
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()

def test_exit_is_idempotent(wired, monkeypatch):
    conn, cur = wired
    monkeypatch.setattr(api.db, "one", lambda *a, **k: {
        "receipt_id": 7, "source_id": 9, "weight": 10, "quantity": 0, "pallets": 0})
    assert api.record_exit(7, 9, Exit(weight=10, request_id=uuid4()), {"id": 1}) == {"recorded": True}
    cur.execute.assert_not_called()

def test_original_invoice_with_registered_stock_cannot_be_cancelled(monkeypatch):
    from app.routers import invoice
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(invoice, "get_connection", lambda: conn)
    monkeypatch.setattr(invoice.db, "one", MagicMock(side_effect=[
        {"tally_id": 10}, {"id_tali": 10}, {"ghabz_id": 7, "non_customs_count": 1}]))
    with pytest.raises(HTTPException) as exc:
        invoice.cancel_invoice(30, {"id": 1})
    assert exc.value.status_code == 409
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


from app.services.non_customs import BatchRegistration

@pytest.fixture
def batch_wired(wired, monkeypatch):
    conn, cur = wired
    monkeypatch.setattr(api.db, "lock_tally", MagicMock())
    sources = [{"receipt_id": rid, "source_id": sid, "tally_id": 10,
        "invoice_id": 30 + rid, "invoice_date": datetime(2026, 1, 1),
        "cargo": "weight", "weight": 100, "quantity": 20, "pallets": 0}
        for rid, sid in [(7, 9), (8, 11)]]
    monkeypatch.setattr(api.db, "rows", lambda *a, **k: sources)
    return conn, cur

def batch_payload(rows):
    return BatchRegistration(start_date=date(2026, 1, 2), settlement_confirmed=True, rows=rows)

def test_batch_saves_multiple_rows_and_receipts_of_one_tally(batch_wired):
    conn, cur = batch_wired
    result = api.register_many(10, batch_payload([
        {"receipt_id": 7, "source_id": 9, "weight": 40},
        {"receipt_id": 8, "source_id": 11, "weight": 25}]), {"id": 1})
    assert result == {"registered": True, "count": 2}
    assert [call.args[1]["weight"] for call in cur.execute.call_args_list] == [40, 25]
    conn.commit.assert_called_once()
    api.db.lock_tally.assert_called_once_with(cur, 10)

@pytest.mark.parametrize("second", [
    {"receipt_id": 7, "source_id": 9, "weight": 10},
    {"receipt_id": 8, "source_id": 11, "weight": 101},
    {"receipt_id": 99, "source_id": 11, "weight": 10},
])
def test_invalid_batch_never_partially_saves(batch_wired, second):
    conn, cur = batch_wired
    with pytest.raises(HTTPException):
        api.register_many(10, batch_payload([
            {"receipt_id": 7, "source_id": 9, "weight": 40}, second]), {"id": 1})
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()

def test_batch_rejects_rows_from_another_tally(batch_wired):
    conn, cur = batch_wired
    with pytest.raises(HTTPException):
        api.register_many(20, batch_payload([
            {"receipt_id": 7, "source_id": 9, "weight": 40}]), {"id": 1})
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()
