"""Cancellation preserves source records and reopens invoice issuance."""
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.routers import invoice as api
from app.services import receipt_db as db


@pytest.fixture
def wired(monkeypatch):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api, "get_connection", lambda: conn)
    one = MagicMock(side_effect=[{"tally_id": 10}, {"id_tali": 10}, {"ghabz_id": 20}])
    monkeypatch.setattr(db, "one", one)
    return conn, cur, one


def test_cancel_only_soft_deletes_invoice_and_releases_receipt(wired):
    conn, cur, one = wired
    assert api.cancel_invoice(5, {"id": 7}) is None
    assert 'FOR UPDATE' in one.call_args_list[1].args[1]
    writes = cur.execute.call_args_list
    assert len(writes) == 2
    sql, params = writes[0].args
    assert 'UPDATE "FA_SORAT_HESAB_HEADER"' in sql
    assert '"SORAT_IS_DELETED" = \'yes\'' in sql
    assert params == {"id": 5, "actor": 7}
    sql, params = writes[1].args
    assert '"WORKFLOW_STATUS" = \'finalized\'' in sql
    assert 'NOT EXISTS' in sql  # another active invoice must keep receipt locked
    assert 'NVL("SORAT_IS_DELETED", \'no\') = \'no\'' in sql
    assert '"IS_DELETED" = \'yes\'' not in sql
    assert params == {"id": 20}
    conn.commit.assert_called_once()


@pytest.mark.parametrize("answers", [[None], [{"tally_id": 10}, {}, None]])
def test_missing_or_concurrently_cancelled_invoice_does_not_write(wired, answers):
    conn, cur, one = wired
    one.side_effect = answers
    with pytest.raises(HTTPException) as exc:
        api.cancel_invoice(5, {"id": 7})
    assert exc.value.status_code == 404
    cur.execute.assert_not_called()
    conn.commit.assert_not_called()


def test_legacy_invoice_without_receipt_can_be_cancelled(wired):
    conn, cur, one = wired
    one.side_effect = [{"tally_id": None}, {"ghabz_id": None}]
    api.cancel_invoice(5, {"id": 7})
    assert cur.execute.call_count == 1
    conn.commit.assert_called_once()


def test_receipt_update_failure_does_not_commit_invoice_delete(wired):
    conn, cur, _ = wired
    cur.execute.side_effect = [None, RuntimeError("write failed")]
    with pytest.raises(RuntimeError):
        api.cancel_invoice(5, {"id": 7})
    conn.commit.assert_not_called()


def test_list_and_detail_exclude_cancelled_invoices():
    for sql in (api.INVOICE_LIST_SQL, api.INVOICE_HEADER_SQL):
        assert 'NVL(s."SORAT_IS_DELETED", \'no\') = \'no\'' in sql
