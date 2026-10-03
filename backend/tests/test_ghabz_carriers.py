import sqlite3
import pytest
from app.routers.ghabz import CARRIERS_SQL


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE fa_ghabz_anbar_header (ID_ghabz INT, TALI_ID INT, IS_DELETED TEXT, IS_MASTER TEXT);
        CREATE TABLE FA_TALI_DETAILES (ID_TALI_DETAILS INT, ID_HEADERS_TALI INT, IS_DELETED TEXT, NUMBER_HAMEL TEXT, HSCODE TEXT);
        CREATE TABLE FA_GHABZ_TALLY_SOURCE (RECEIPT_ID INT, TALLY_DETAIL_ID INT, QUANTITY_SHARE REAL, WEIGHT_SHARE REAL, BASKOL_SHARE REAL);
        CREATE TABLE FA_ghabz_anbar_DETAILES (ID_GHABZ_ANBAR_HEADAR INT, IS_DELETED TEXT, NUMBER_HAMEL TEXT, HSCODE TEXT);
        INSERT INTO fa_ghabz_anbar_header VALUES (858, 1, 'no', 'yes'), (859, 1, 'no', 'no');
        INSERT INTO FA_TALI_DETAILES VALUES
            (1,1,'no',' A ','hs1'), (2,1,'no','B','HS1'), (3,1,'no','A','HS1'),
            (4,1,'no','C','HS2'), (5,1,'yes','DELETED','HS1'), (6,2,'no','OTHER','HS1');
        INSERT INTO FA_ghabz_anbar_DETAILES VALUES (858,'no','A','HS1'), (859,'no','A','HS1');
    """)
    yield conn
    conn.close()


def carriers(db, receipt=858):
    return [r[0] for r in db.execute(CARRIERS_SQL, {"hid": receipt})]


def test_master_includes_all_live_carriers_without_duplicates(db):
    assert carriers(db) == ['A', 'B', 'C']


def test_explicit_links_take_precedence_over_shared_hscode(db):
    db.executescript("""
        INSERT INTO FA_GHABZ_TALLY_SOURCE VALUES (859,2,1,1,1), (859,4,1,1,1), (859,1,0,0,0);
    """)
    assert carriers(db, 859) == ['B', 'C']


def test_legacy_grouped_goods_include_every_matching_carrier(db):
    assert carriers(db, 859) == ['A', 'B']


def test_standalone_receipt_falls_back_to_saved_carriers(db):
    db.execute("UPDATE fa_ghabz_anbar_header SET TALI_ID=NULL WHERE ID_ghabz=859")
    assert carriers(db, 859) == ['A']


def test_deleted_receipt_has_no_carriers(db):
    db.execute("UPDATE fa_ghabz_anbar_header SET IS_DELETED='yes' WHERE ID_ghabz=858")
    assert carriers(db) == []


def test_line_carriers_are_limited_to_its_hscode(db):
    from app.routers.ghabz import LINE_CARRIERS_SQL
    rows = db.execute(LINE_CARRIERS_SQL, {"hid": 858, "hscode": "HS1"})
    assert [r[0] for r in rows] == ['A', 'B']


def test_line_carriers_respect_explicit_allocations(db):
    from app.routers.ghabz import LINE_CARRIERS_SQL
    db.executescript("""
        INSERT INTO FA_GHABZ_TALLY_SOURCE VALUES (859,2,1,1,1), (859,4,1,1,1);
    """)
    rows = db.execute(LINE_CARRIERS_SQL, {"hid": 859, "hscode": "HS1"})
    assert [r[0] for r in rows] == ['B']
