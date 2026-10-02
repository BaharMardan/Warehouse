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
    monkeypatch.setattr(api.db, "rows", lambda *a: [row(), row(80, 2)])
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
    monkeypatch.setattr(api.db, "rows", lambda *a: [row()])
    cur.execute.side_effect = [None, RuntimeError("failed")]
    with pytest.raises(RuntimeError):
        api.mark_seen(api.SeenInput(tokens=[token]), {"id": 7})
    conn.commit.assert_not_called()
    conn.rollback.assert_called_once()

def test_abandoned_permission_is_independent():
    from app.auth.permissions import effective_permissions
    assert "abandoned.view" not in effective_permissions(granted=["tally.view"], is_admin=False)
    assert {"abandoned.view", "tally.view"} <= effective_permissions(granted=["abandoned.view"], is_admin=False)
