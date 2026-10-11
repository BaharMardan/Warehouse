from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.routers import receipt_workflow as api
from app.routers import tally_handoff as handoff
from app.services import receipt_db as db
from app.auth.permissions import effective_permissions


def setup_receipt(monkeypatch, status="finalized", active=0, sibling_status="finalized"):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    current = {"id": 1, "tally_id": 10, "is_master": "no", "status": status,
               "requires_invoice": "yes", "line_count": 1}
    sibling = {**current, "id": 2, "status": sibling_status}
    monkeypatch.setattr(db, "receipt", lambda *a, **k: (current, [current, sibling], {}))
    monkeypatch.setattr(db, "one", lambda *a, **k: {"cnt": active})
    monkeypatch.setattr(api, "get_workflow", lambda rid: {"id": rid})
    return conn


@pytest.mark.parametrize("status,active,sibling", [
    ("invoice_issued", 1, "finalized"),
    ("finalized", 1, "finalized"), ("finalized", 0, "invoice_issued"),
])
def test_return_rejects_invalid_state_or_active_invoice(monkeypatch, status, active, sibling):
    conn = setup_receipt(monkeypatch, status, active, sibling)
    with pytest.raises(HTTPException) as exc:
        api.return_receipt(1, {"id": 5})
    assert exc.value.status_code == 409
    conn.commit.assert_not_called()
    conn.cursor.return_value.__enter__.return_value.execute.assert_not_called()


def test_return_reopens_all_finalized_receipts_and_discards_shared_prices(monkeypatch):
    conn = setup_receipt(monkeypatch)
    assert api.return_receipt(1, {"id": 5}) == {"id": 1}
    calls = conn.cursor.return_value.__enter__.return_value.execute.call_args_list
    assert len(calls) == 3
    assert '"TALI_ID" = :tid' in calls[0].args[0]
    assert '"ALLOCATION_RATIO" = NULL' in calls[0].args[0]
    assert "FA_RECEIPT_SERVICE_POOL" in calls[1].args[0]
    assert calls[2].args[1]["actor"] == 5
    conn.commit.assert_called_once()


@pytest.mark.parametrize("step,target", [("keeper", "operator"), ("returned", "keeper")])
def test_tally_previous_step(monkeypatch, step, target):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(handoff, "get_connection", lambda: conn)
    monkeypatch.setattr(handoff, "lock_tally", lambda *a: (step, None, None))
    monkeypatch.setattr(db, "receipts", lambda *a: [])
    monkeypatch.setattr(handoff, "read_handoff", lambda *a: {"step": target})
    assert handoff.previous_step(10, {"id": 5}) == {"step": target}
    call = conn.cursor.return_value.__enter__.return_value.execute.call_args
    assert call.args[1]["step"] == target
    conn.commit.assert_called_once()


@pytest.mark.parametrize("step,receipts", [("operator", []), ("returned", [{"id": 1}])])
def test_tally_return_requires_no_receipts_and_a_previous_stage(monkeypatch, step, receipts):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(handoff, "get_connection", lambda: conn)
    monkeypatch.setattr(handoff, "lock_tally", lambda *a: (step, None, None))
    monkeypatch.setattr(db, "receipts", lambda *a: receipts)
    with pytest.raises(HTTPException):
        handoff.previous_step(10, {"id": 5})
    conn.commit.assert_not_called()


def test_forward_permissions_do_not_grant_return():
    granted = effective_permissions(is_admin=False, granted=["tally.edit", "tally.services", "invoice.issue"])
    assert "workflow.return" not in granted


def test_pending_receipt_can_explicitly_enter_correction_mode(monkeypatch):
    conn = setup_receipt(monkeypatch, "created", 0, "created")
    assert api.return_receipt(1, {"id": 5}) == {"id": 1}
    conn.commit.assert_called_once()


@pytest.mark.parametrize("step,statuses,count,expected", [
    ("keeper", ["sent_to_keeper"], 0, True),
    ("keeper", ["sent_to_keeper", "sent_to_keeper"], 0, True),
    ("keeper", ["sent_to_keeper"], 1, False),
    ("returned", ["sent_to_keeper"], 0, False),
    ("keeper", ["created"], 0, False),
    ("keeper", ["sent_to_keeper", "finalized"], 0, False),
    ("keeper", ["sent_to_keeper", "invoice_issued"], 0, False),
    ("keeper", [], 0, False),
])
def test_correction_requires_all_receipts_reopened_and_no_active_invoices(step, statuses, count, expected):
    assert db.correction_open(step, [{"status": s} for s in statuses], count) is expected


@pytest.mark.parametrize("action,values", [
    ("update", {"insured_value": 100}),
    ("update", {"weighte": 50, "hscode": "123"}),
    ("delete", {}),
    ("create", {"id_headers_tali": 10}),
])
def test_all_goods_writes_are_allowed_after_return_and_invalidate_derived_allocations(monkeypatch, action, values):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.rowcount = 1
    cur.var.return_value.getvalue.return_value = [7]
    monkeypatch.setattr(db, "get_connection", lambda: conn)
    monkeypatch.setattr(db, "one", lambda *a: {"id_headers_tali": 10, "cnt": 0})
    monkeypatch.setattr(db, "lock_tally", lambda *a: {"handoff_step": "keeper"})
    monkeypatch.setattr(db, "receipts", lambda *a: [{"status": "sent_to_keeper"}])
    assert db.guarded_write("FA_TALI_DETAILES", "ID_TALI_DETAILS", action, "mutate",
                            {}, row_id=None if action == "create" else 1, values=values) in (1, 7)
    writes = cur.execute.call_args_list
    assert len(writes) == 4
    for name, call in zip(("FA_RECEIPT_PALLETS", "FA_GHABZ_TALLY_SOURCE", "FA_RECEIPT_SERVICE_POOL"), writes):
        assert name in call.args[0]
        assert call.args[1] == {"tid": 10}
    assert writes[-1].args[0] == "mutate"
    conn.commit.assert_called_once()


def test_active_invoice_blocks_goods_write_even_with_stale_reopened_status(monkeypatch):
    cur = MagicMock()
    monkeypatch.setattr(db, "lock_tally", lambda *a: {"handoff_step": "keeper"})
    monkeypatch.setattr(db, "receipts", lambda *a: [{"status": "sent_to_keeper"}])
    monkeypatch.setattr(db, "active_invoice_count", lambda *a: 1)
    with pytest.raises(HTTPException) as exc:
        db.guard_source(cur, 10, allow_correction=True)
    assert exc.value.status_code == 409
    cur.execute.assert_not_called()


def test_tally_deletion_remains_blocked_when_receipts_exist(monkeypatch):
    monkeypatch.setattr(db, "lock_tally", lambda *a: {"handoff_step": "keeper"})
    monkeypatch.setattr(db, "receipts", lambda *a: [{"status": "sent_to_keeper"}])
    with pytest.raises(HTTPException):
        db.guard_source(MagicMock(), 10)


@pytest.mark.parametrize("count,goods", [(0, True), (1, False)])
def test_handoff_reports_goods_editability_consistently_with_backend_guard(monkeypatch, count, goods):
    cur = MagicMock()
    cur.description = [("ID_TALI",), ("STEP",)]
    cur.fetchone.return_value = (10, "keeper")
    monkeypatch.setattr(db, "receipts", lambda *a: [{
        "id": 1, "number_text": "20", "status": "sent_to_keeper", "is_master": "no", "line_count": 1}])
    monkeypatch.setattr(db, "one", lambda *a: {"cnt": count})
    monkeypatch.setattr(handoff.rp, "tally_rows", lambda *a: [])
    state = handoff.read_handoff(cur, 10)
    assert state["can_edit_goods"] is goods
    assert state["active_invoice_count"] == count
