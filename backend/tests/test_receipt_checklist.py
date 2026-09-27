"""Receipt eligibility and proportional charge allocation regression tests."""
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.services.receipt_allocation import allocation_ratio, allocated_amount
from app.services import receipt_db
from app.routers import receipt_workflow as api


def receipt(status="created", is_master="no", rid=1):
    return {"id": rid, "tally_id": 10, "is_master": is_master, "status": status,
            "requires_invoice": "yes", "line_count": 1, "allocation_ratio": None}


@pytest.mark.parametrize("cargo", ["weight", "container"])
def test_weight_and_container_charges_follow_original_linked_weight(cargo):
    ratio = allocation_ratio(False, cargo, 30, 100, None, None)
    assert allocated_amount(1000, ratio) == 300
    assert allocated_amount(1000, Decimal(".7"), ratio, 300) == 700


def test_volumetric_uses_keeper_pallets_instead_of_weight():
    assert allocation_ratio(False, "volumetric", 90, 100, 30, 100) == Decimal(".3")
    assert allocation_ratio(False, "yes", 90, 100, 30, 100) == Decimal(".3")


def test_general_receipt_gets_whole_pool():
    assert allocation_ratio(True, "weight", 100, 100, None, None) == 1


@pytest.mark.parametrize("weight,total,pallets,total_pallets,cargo", [
    (101, 100, None, None, "weight"), (1, 0, None, None, "weight"),
    (1, 100, None, 100, "volumetric"), (1, 100, 101, 100, "volumetric"),
    (1, 100, 1, None, "volumetric"), (1, 100, 1, 100, None),
])
def test_invalid_allocation_is_rejected(weight, total, pallets, total_pallets, cargo):
    with pytest.raises(ValueError):
        allocation_ratio(False, cargo, weight, total, pallets, total_pallets)


def test_rounding_remainder_is_allocated_once():
    first = allocated_amount(1, Decimal(".3"))
    second = allocated_amount(1, Decimal(".7"), Decimal(".3"), first)
    assert first + second == 1
    with pytest.raises(ValueError):
        allocated_amount(1000, Decimal(".7"), Decimal(".4"), 400)


def test_general_summary_has_neither_action():
    general, detail = receipt(is_master="yes"), receipt(rid=2)
    state = receipt_db.workflow(general, [general, detail])
    assert not state["show_checklist"] and not state["show_invoice"]
    assert receipt_db.workflow(detail, [general, detail])["show_checklist"]
    assert receipt_db.workflow(general, [general])["show_checklist"]


@pytest.mark.parametrize("status", ["created", "sent_to_keeper"])
def test_invoice_api_rejects_pending_receipts(monkeypatch, status):
    current = receipt(status)
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    monkeypatch.setattr(receipt_db, "receipt", lambda *a, **k: (current, [current], {}))
    monkeypatch.setattr(receipt_db, "one", lambda *a, **k: None)
    with pytest.raises(HTTPException) as exc:
        api.issue_invoice(1, {"id": 1})
    assert exc.value.status_code == 409
    conn.commit.assert_not_called()


def test_retry_does_not_duplicate_invoice(monkeypatch):
    current = receipt("invoice_issued")
    conn = MagicMock()
    conn.__enter__.return_value = conn
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    monkeypatch.setattr(receipt_db, "receipt", lambda *a, **k: (current, [current], {}))
    monkeypatch.setattr(receipt_db, "one", lambda *a, **k: {"id": 700})
    assert api.issue_invoice(1, {"id": 1}) == {"invoice_id": 700}
    conn.cursor.return_value.__enter__.return_value.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_services_lock_across_related_receipts(monkeypatch):
    monkeypatch.setattr(receipt_db, "lock_tally", lambda *a: {"handoff_step": "returned"})
    monkeypatch.setattr(receipt_db, "receipts", lambda *a: [receipt("finalized"), receipt(rid=2)])
    with pytest.raises(HTTPException):
        receipt_db.guard_services(MagicMock(), 10)


def test_pending_receipts_reopen_keeper_services(monkeypatch):
    monkeypatch.setattr(receipt_db, "lock_tally", lambda *a: {"handoff_step": "returned"})
    monkeypatch.setattr(receipt_db, "receipts", lambda *a: [receipt()])
    receipt_db.guard_services(MagicMock(), 10)


def test_invoice_goods_query_uses_original_details_only():
    assert '"FA_TALI_DETAILES"' in api.RECEIPT_STORAGE_SQL
    assert '"FA_GHABZ_TALLY_SOURCE"' in api.RECEIPT_STORAGE_SQL
    assert '"FA_ghabz_anbar_DETAILES"' not in api.RECEIPT_STORAGE_SQL
    assert '"storage_price"' in api.RECEIPT_STORAGE_SQL


def test_service_snapshot_reads_service_totals_once_without_receipt_aggregation(monkeypatch):
    calls = []
    def rows(_cur, sql, params=None):
        calls.append(sql)
        if sql == api.RECEIPT_STORAGE_SQL:
            return [{"id": 1}]
        return [{"price": 1000, "number_service": 1}] if sql == api.OTHER_SERVICE_SQL else []
    monkeypatch.setattr(receipt_db, "rows", rows)
    monkeypatch.setattr(receipt_db, "one", lambda *a, **k: {"carrier_count": 0})
    charges = api.snapshot_services(MagicMock(), receipt())
    assert calls.count(api.OTHER_SERVICE_SQL) == 1
    assert sum(c.price for c in charges) == 1000     # services only; storage is never pooled


def test_service_snapshot_requires_linked_tally_rows(monkeypatch):
    monkeypatch.setattr(receipt_db, "rows", lambda *a, **k: [])
    with pytest.raises(HTTPException) as exc:
        api.snapshot_services(MagicMock(), receipt())
    assert exc.value.status_code == 409


@pytest.mark.parametrize("pending", [True, False])
def test_kartabl_pending_checklist_reopens_keeper_stage(monkeypatch, pending):
    from app.routers import kartabl
    rows = [{"id_tali": 10, "handoff_step": "returned"},
            {"id_tali": 20, "handoff_step": "keeper"},
            {"id_tali": 30, "handoff_step": "returned"}]
    monkeypatch.setattr(kartabl, "fetch_all", lambda sql: rows)
    monkeypatch.setattr(api, "keeper_queue", lambda: [
        {"id": 1, "tally_id": 10}, {"id": 2, "tally_id": 10}
    ] if pending else [])
    result = kartabl.list_kartabl()
    assert len(result) == 3
    assert result[0]["handoff_step"] == ("keeper" if pending else "returned")
    assert result[1]["handoff_step"] == "keeper"
    assert result[2]["handoff_step"] == "returned"
