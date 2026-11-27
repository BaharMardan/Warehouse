"""Regression: voiding and renumbering must reuse the master's identity."""
import sqlite3

import pytest

from app.services.ghabz_numbering import find_master, MasterNumberConflict


@pytest.fixture
def db():
    conn = sqlite3.connect(':memory:')
    conn.create_function('NVL', 2, lambda value, fallback: fallback if value is None else value)
    conn.execute('''CREATE TABLE fa_ghabz_anbar_header (
        ID_ghabz INTEGER PRIMARY KEY, TALI_ID INTEGER, GHABZ_SEQ INTEGER,
        GHABZ_NUMBER TEXT UNIQUE, IS_DELETED TEXT, IS_MASTER TEXT,
        UNIQUE(TALI_ID, GHABZ_SEQ))''')
    yield conn
    conn.close()


@pytest.mark.parametrize('deleted', ['yes', 'no'])
def test_old_master_found_after_tally_number_changes(db, deleted):
    db.execute("INSERT INTO fa_ghabz_anbar_header VALUES (20,1018,0,'1405_55',?,'yes')", (deleted,))
    assert find_master(db.cursor(), 1018, '1405_56') == (20, '1405_55', deleted, 'yes')


def test_new_number_cannot_take_another_receipts_number(db):
    db.execute("INSERT INTO fa_ghabz_anbar_header VALUES (20,1018,0,'1405_55','yes','yes')")
    db.execute("INSERT INTO fa_ghabz_anbar_header VALUES (21,2000,0,'1405_56','no','yes')")
    with pytest.raises(MasterNumberConflict):
        find_master(db.cursor(), 1018, '1405_56')


def test_number_lookup_still_finds_legacy_master_without_sequence(db):
    db.execute("INSERT INTO fa_ghabz_anbar_header VALUES (20,1018,NULL,'1405_56','yes','yes')")
    assert find_master(db.cursor(), 1018, '1405_56')[0] == 20


def test_new_tally_has_no_master(db):
    assert find_master(db.cursor(), 1018, '1405_56') is None


@pytest.mark.parametrize('deleted,live_lines', [('yes', 0), ('no', 1)])
def test_issue_route_rebuilds_void_master_but_blocks_live_master(monkeypatch, deleted, live_lines):
    from datetime import datetime
    from fastapi import HTTPException
    from app.routers import ghabz
    from app.services import handoff_notifications

    class Cursor:
        revived = None
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params=None):
            self.result = None
            if sql == ghabz.REVIVE_MASTER_SQL:
                self.revived = params
            elif 'WHERE "TALI_ID" = :tali_id AND "GHABZ_SEQ" = 0' in sql:
                self.result = (20, '1405_55', deleted, 'yes')
            elif 'WHERE "GHABZ_NUMBER" = :ghabz_number' in sql:
                self.result = None
            elif sql == ghabz.COUNT_LIVE_LINES_SQL:
                self.result = (live_lines,)
            elif 'SELECT SYSDATE' in sql:
                self.result = (datetime(2026, 11, 27),)
            elif sql == ghabz.INSERT_GHABZ:
                raise AssertionError('Must not insert a second sequence-zero receipt')
        def fetchone(self): return self.result
        def executemany(self, sql, rows): pass

    cursor = Cursor()
    class Connection:
        committed = False
        rolled_back = False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def cursor(self): return cursor
        def commit(self): self.committed = True
        def rollback(self): self.rolled_back = True

    conn = Connection()
    monkeypatch.setattr(ghabz, 'get_connection', lambda: conn)
    monkeypatch.setattr(ghabz.receipt_db, 'lock_tally', lambda *a: None)
    monkeypatch.setattr(ghabz.receipt_db, 'receipts', lambda *a: [{'id': 20}])
    fetched = iter([[{'handoff_step': 'keeper'}], [{'hscode': '1234'}]])
    monkeypatch.setattr(ghabz, '_rows_with_columns', lambda *a: next(fetched))
    monkeypatch.setattr(ghabz, 'master_lines', lambda rows: [{'hscode': '1234'}])
    monkeypatch.setattr(ghabz, 'master_number', lambda *a: ('1405_56', 0, '56'))
    monkeypatch.setattr(handoff_notifications, 'record', lambda *a: None)

    if deleted == 'no':
        with pytest.raises(HTTPException) as exc:
            ghabz.create_master_ghabz(1018, {'id': 1})
        assert exc.value.status_code == 400
        assert cursor.revived is None
        assert conn.rolled_back
    else:
        result = ghabz.create_master_ghabz(1018, {'id': 1})
        assert result['id_ghabz'] == 20
        assert result['ghabz_number'] == '1405_56'
        assert result['rebuilt'] is True
        assert cursor.revived == {'header_id': 20, 'actor_id': 1,
                                  'ghabz_number': '1405_56', 'tali_number': '56'}
        assert conn.committed
