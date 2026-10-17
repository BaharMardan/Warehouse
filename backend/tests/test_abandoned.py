from datetime import datetime
from unittest.mock import MagicMock
import pytest
from app.routers import abandoned as api


def row(days=90, tid=1):
    return {"id": tid, "tally_number": str(tid), "age_days": days,
            "unloaded_at": datetime(2026, 1, 1), "owner_name": None}


@pytest.mark.parametrize("days,stage,remaining", [(79, None, None), (80, "warning", 10),
    (89, "warning", 1), (90, "abandoned", 0), (120, "abandoned", 0)])
def test_calendar_boundaries(days, stage, remaining):
    items = api.classify([row(days)], set())
    if stage is None:
        assert items == []
    else:
        assert items[0]["stage"] == stage
        assert items[0]["days_remaining"] == remaining


def test_transition_to_abandoned_is_a_new_event():
    warning = api.classify([row(80)], set())[0]
    assert not api.classify([row(89)], {warning["token"]})[0]["unseen"]
    assert api.classify([row(90)], {warning["token"]})[0]["unseen"]


@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    return conn, cur


def test_users_have_independent_seen_state(wired, monkeypatch):
    token = api.classify([row()], set())[0]["token"]
    def rows(cur, sql, params=None):
        if sql == api.AGING_SQL:
            return [row(), row(80, 2)]
        if sql == api.GOODS_SQL:
            return []
        return [{"event_token": token}] if params["id"] == 1 else []
    monkeypatch.setattr(api.db, "rows", rows)
    first = api.list_abandoned({"id": 1})
    second = api.list_abandoned({"id": 2})
    assert not first["items"][0]["unseen"]
    assert second["items"][0]["unseen"]
    assert first["total"] == 2
    assert first["abandoned_count"] == first["warning_count"] == 1


def test_seen_only_acknowledges_displayed_current_tokens(wired, monkeypatch):
    conn, cur = wired
    items = api.classify([row(), row(80, 2)], set())
    monkeypatch.setattr(api.db, "rows", lambda cur, sql, *a: [] if sql == api.GOODS_SQL else [row(), row(80, 2)])
    api.mark_seen(api.SeenInput(tokens=[items[0]["token"], "invalid"]), {"id": 7})
    assert cur.execute.call_count == 2  # user lock + the one displayed event
    assert cur.execute.call_args.args[1] == {"viewer_id": 7, "token": items[0]["token"]}
    conn.commit.assert_called_once()


def test_filters_exclude_deleted_exited_and_invoiced_tallies():
    sql = api.AGING_SQL
    assert 'h."IS_DELETED" = \'no\'' in sql
    assert 'h."DATE_UNLOADING" IS NOT NULL' in sql
    assert 'h."DATE_CARGO_EXIT" IS NULL OR TRUNC(h."DATE_CARGO_EXIT") >' in sql
    assert 'NOT EXISTS' in sql
    assert 'NVL(i."SORAT_IS_DELETED", \'no\') = \'no\'' in sql
    assert "Asia/Tehran" in sql


def test_seen_failure_rolls_back(wired, monkeypatch):
    conn, cur = wired
    token = api.classify([row()], set())[0]["token"]
    monkeypatch.setattr(api.db, "rows", lambda cur, sql, *a: [] if sql == api.GOODS_SQL else [row()])
    cur.execute.side_effect = [None, RuntimeError("failed")]
    with pytest.raises(RuntimeError):
        api.mark_seen(api.SeenInput(tokens=[token]), {"id": 7})
    conn.commit.assert_not_called()
    conn.rollback.assert_called_once()

def test_abandoned_permission_is_independent():
    from app.auth.permissions import effective_permissions
    assert "abandoned.view" not in effective_permissions(granted=["tally.view"], is_admin=False)
    assert {"abandoned.view", "tally.view"} <= effective_permissions(granted=["abandoned.view"], is_admin=False)


def goods(tid=1, detail=10, receipt=None, weight=100, value=200):
    return {"tally_id": tid, "detail_id": detail, "receipt_id": receipt,
            "receipt_number": str(receipt) if receipt else None, "hscode": "123",
            "description": "cargo", "remaining_weight": weight, "customs_value": value}


def test_multiple_receipts_do_not_multiply_goods_weights_or_customs_values():
    items = api.attach_goods(api.classify([row()], set()),
        [goods(receipt=20), goods(receipt=21), goods(receipt=20)])
    assert len(items) == len(items[0]["goods"]) == 1
    line = items[0]["goods"][0]
    assert line["remaining_weight"] == 100
    assert line["customs_value"] == 200
    assert line["receipts"] == [{"id": 20, "number": "20"}, {"id": 21, "number": "21"}]


def test_rows_with_same_hscode_stay_separate_and_unreceipted_cargo_is_retained():
    items = api.attach_goods(api.classify([row()], set()), [goods(detail=10), goods(detail=11, weight=50)])
    assert [line["detail_id"] for line in items[0]["goods"]] == [10, 11]
    assert [line["remaining_weight"] for line in items[0]["goods"]] == [100, 50]
    assert all(line["receipts"] == [] for line in items[0]["goods"])


def test_report_keeps_tally_counters_and_seen_state_when_multiple_goods_exist(wired, monkeypatch):
    token = api.classify([row()], set())[0]["token"]
    def rows(cur, sql, params=None):
        if sql == api.AGING_SQL:
            return [{**row(), "order_registration_number": "00123"}]
        if sql == api.GOODS_SQL:
            return [goods(), goods(detail=11)]
        return [{"event_token": token}]
    monkeypatch.setattr(api.db, "rows", rows)
    result = api.list_abandoned({"id": 1})
    assert result["total"] == result["abandoned_count"] == 1
    assert not result["has_unseen"]
    assert len(result["items"][0]["goods"]) == 2
    assert result["items"][0]["order_registration_number"] == "00123"


def test_empty_tallies_are_not_lost_and_unrelated_goods_are_ignored():
    items = api.attach_goods(api.classify([row()], set()), [goods(tid=2)])
    assert len(items) == 1 and items[0]["goods"] == []


def test_goods_query_uses_exact_sources_with_legacy_hscode_fallback():
    assert "FA_GHABZ_TALLY_SOURCE" in api.GOODS_SQL
    assert 'src."TALLY_DETAIL_ID" = d."ID_TALI_DETAILS"' in api.GOODS_SQL
    assert 'rd."IS_DELETED" = \'no\'' in api.GOODS_SQL
    assert 'r."IS_DELETED" = \'no\'' in api.GOODS_SQL
    assert 'd."IS_DELETED" = \'no\'' in api.GOODS_SQL


def billed(detail=10, receipt=20, share="0.4", weight=100, hs="123"):
    return {**goods(detail=detail, receipt=receipt, weight=weight),
            "hscode": hs, "invoiced": 1, "source_detail_id": detail,
            "weight_share": share, "quantity_share": share, "baskol_share": share}


def test_partial_invoice_keeps_only_uninvoiced_weight_and_pending_receipt_number():
    items = api.attach_goods(api.classify([row()], set()),
        [billed(), goods(receipt=21)])
    assert len(items) == 1
    assert items[0]["goods"][0]["remaining_weight"] == 60
    assert items[0]["goods"][0]["receipts"] == [{"id": 21, "number": "21"}]


def test_fully_invoiced_tally_leaves_the_abandoned_list():
    assert api.attach_goods(api.classify([row()], set()), [billed(share="1")]) == []


def test_cancelled_invoice_restores_all_stock():
    cancelled = {**billed(), "invoiced": 0}
    items = api.attach_goods(api.classify([row()], set()), [cancelled])
    assert items[0]["goods"][0]["remaining_weight"] == 100


def test_multiple_invoices_and_duplicate_receipt_rows_cannot_double_consume():
    items = api.attach_goods(api.classify([row()], set()),
        [billed(share="0.2"), billed(share="0.2"), billed(receipt=21, share="0.3")])
    assert items[0]["goods"][0]["remaining_weight"] == 50


def test_legacy_invoice_deducts_weight_once_across_repeated_hscode():
    legacy = [{"invoiced": 1, "source_detail_id": None, "receipt_weight": 120,
               **goods(detail=detail, receipt=20)} for detail in (10, 11)]
    items = api.attach_goods(api.classify([row()], set()), legacy)
    assert len(items[0]["goods"]) == 1
    assert items[0]["goods"][0]["detail_id"] == 11
    assert items[0]["goods"][0]["remaining_weight"] == 80


def test_legacy_receipts_use_exact_reservations_before_hscode_fallback():
    legacy = [{"invoiced": 1, "source_detail_id": None, "receipt_weight": 50,
               **goods(detail=detail, receipt=20)} for detail in (10, 11)]
    items = api.attach_goods(api.classify([row()], set()),
        [*legacy, billed(detail=10, receipt=21, share="1")])
    assert len(items[0]["goods"]) == 1
    assert items[0]["goods"][0]["detail_id"] == 11
    assert items[0]["goods"][0]["remaining_weight"] == 50


def test_unweighed_cargo_uses_remaining_quantity_to_detect_full_invoicing():
    partial = {**billed(weight=0, share="0.5"), "quantity": 10}
    assert len(api.attach_goods(api.classify([row()], set()), [partial])) == 1
    full = {**partial, "quantity_share": 1}
    assert api.attach_goods(api.classify([row()], set()), [full]) == []


def test_invoicing_one_good_does_not_hide_another_good():
    items = api.attach_goods(api.classify([row()], set()),
        [billed(share="1"), goods(detail=11, weight=70)])
    assert len(items) == 1
    assert [g["detail_id"] for g in items[0]["goods"]] == [11]


def test_partial_tally_remains_counted_and_fully_invoiced_tally_is_removed(wired, monkeypatch):
    def rows(cur, sql, params=None):
        if sql == api.AGING_SQL:
            return [row(), row(tid=2)]
        if sql == api.GOODS_SQL:
            return [billed(), {**billed(share="1"), "tally_id": 2}]
        return []
    monkeypatch.setattr(api.db, "rows", rows)
    result = api.list_abandoned({"id": 1})
    assert result["total"] == result["abandoned_count"] == 1
    assert result["items"][0]["id"] == 1
    assert result["items"][0]["goods"][0]["remaining_weight"] == 60


def test_supplemental_invoices_do_not_consume_the_same_cargo_again():
    assert '"FA_REMAINING_INVOICE"' in api.GOODS_SQL
    assert 'extra."INVOICE_ID" = i."ID_SORAT"' in api.GOODS_SQL
