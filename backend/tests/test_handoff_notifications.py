"""Exercise the actual feed SQL with SQLite; Oracle-specific writes use an adapter."""
import sqlite3
from unittest.mock import MagicMock

import pytest

from app.services import handoff_notifications as events


class Variable:
    def getvalue(self):
        return [self.value]


class Cursor:
    """Only adapts Oracle RETURNING INTO; the feed SELECT runs unchanged."""
    def __init__(self, connection):
        self.cursor = connection.cursor()

    def var(self, _):
        return Variable()

    def execute(self, sql, params=None):
        params = dict(params or {})
        if "RETURNING" in sql:
            variable = params.pop("event_id")
            sql = sql.replace('RETURNING "VERSION" INTO :event_id', 'RETURNING "VERSION"')
            self.cursor.execute(sql, params)
            variable.value = self.cursor.fetchone()[0]
        else:
            self.cursor.execute(sql, params)

    def fetchone(self):
        return self.cursor.fetchone()


@pytest.fixture
def database():
    connection = sqlite3.connect(":memory:")
    connection.executescript("""
        CREATE TABLE FA_HANDOFF_CLOCK (ID INTEGER PRIMARY KEY, VERSION INTEGER);
        INSERT INTO FA_HANDOFF_CLOCK VALUES (1, 0);
        CREATE TABLE FA_HANDOFF_EVENTS (
            ID INTEGER PRIMARY KEY, TARGET TEXT, TALLY_ID INTEGER,
            RECEIPT_ID INTEGER, ACTOR_ID INTEGER
        );
    """)
    yield connection, Cursor(connection)
    connection.close()


def test_every_transition_survives_even_when_same_document_leaves_the_queue(database):
    connection, cursor = database
    baseline = events.read(cursor, None, ["keeper", "operator"], 99)
    events.record(cursor, "keeper", 10, 1)
    events.record(cursor, "operator", 10, 2)
    events.record(cursor, "keeper", 10, 1)
    connection.commit()
    result = events.read(cursor, int(baseline["cursor"]), ["keeper", "operator"], 99)
    assert result == {"cursor": "3", "keeper": 2, "operator": 1}
    assert events.read(cursor, 3, ["keeper", "operator"], 99) == {
        "cursor": "3", "keeper": 0, "operator": 0}


def test_baseline_does_not_replay_existing_events(database):
    _, cursor = database
    events.record(cursor, "keeper", 10, 1)
    assert events.read(cursor, None, ["keeper"], 2) == {
        "cursor": "1", "keeper": 0, "operator": 0}


def test_feed_obeys_recipient_permissions_and_excludes_senders(database):
    _, cursor = database
    events.record(cursor, "keeper", 10, 1)
    events.record(cursor, "operator", 10, 2)
    events.record(cursor, "keeper", 11, 3)
    assert events.read(cursor, 0, ["keeper"], 1) == {
        "cursor": "3", "keeper": 1, "operator": 0}
    assert events.read(cursor, 0, ["operator"], 1) == {
        "cursor": "3", "keeper": 0, "operator": 1}


def test_failed_document_transaction_also_rolls_back_notification_and_clock(database):
    connection, cursor = database
    events.record(cursor, "keeper", 10, 1)
    connection.rollback()
    assert events.read(cursor, 0, ["keeper"], 2) == {
        "cursor": "0", "keeper": 0, "operator": 0}
    events.record(cursor, "keeper", 11, 1)
    assert events.read(cursor, 0, ["keeper"], 2)["keeper"] == 1


@pytest.mark.parametrize("permissions,expected", [
    ([], []), (["tally.view", "ghabz.view"], []),
    (["tally.services"], ["keeper"]), (["tally.edit"], ["operator"]),
    (["ghabz.issue"], ["operator"]),
    (["tally.services", "ghabz.issue"], ["keeper", "operator"]),
])
def test_delivery_targets_follow_permissions(permissions, expected):
    assert events.targets_for(permissions) == expected


def test_invalid_target_never_writes():
    cursor = MagicMock()
    with pytest.raises(ValueError):
        events.record(cursor, "everyone", 1, 2)
    cursor.execute.assert_not_called()


def test_cursor_does_not_lose_precision():
    cursor = MagicMock()
    cursor.fetchone.return_value = (9007199254740993, 2, 1)
    assert events.read(cursor, 0, ["keeper", "operator"], 1)["cursor"] == "9007199254740993"


def test_notification_endpoint_rejects_unrelated_roles_before_reading_database(monkeypatch):
    from fastapi import HTTPException
    from app.routers import kartabl
    connect = MagicMock()
    monkeypatch.setattr(kartabl, "get_connection", connect)
    with pytest.raises(HTTPException) as exc:
        kartabl.handoff_events(after=0, user={"id": 5, "permissions": ["reports.view"]})
    assert exc.value.status_code == 403
    connect.assert_not_called()


@pytest.mark.parametrize("direction", ["keeper", "operator"])
def test_tally_notification_failure_prevents_document_commit(monkeypatch, direction):
    from app.routers import tally_handoff as api
    connection = MagicMock()
    connection.__enter__.return_value = connection
    monkeypatch.setattr(api, "get_connection", lambda: connection)
    monkeypatch.setattr(api, "lock_tally", lambda *args: (
        "operator" if direction == "keeper" else "keeper", "weight", None))
    monkeypatch.setattr(api.receipt_db, "receipts", lambda *args: [])
    monkeypatch.setattr(api, "read_handoff", lambda *args: {"step": direction})
    connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
    notify = MagicMock(side_effect=RuntimeError("event write failed"))
    monkeypatch.setattr(events, "record", notify)
    action = api.send_to_keeper if direction == "keeper" else api.return_to_operator
    with pytest.raises(RuntimeError, match="event write failed"):
        action(10, {"id": 5})
    assert notify.call_args.args[1:] == (direction, 10, 5)
    connection.commit.assert_not_called()
