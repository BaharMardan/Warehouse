import sqlite3
from app.routers.ghabz import DESCRIPTIONS_SQL, receipt_descriptions


def test_distinct_descriptions_count_all_original_rows():
    sources = [dict(hscode=' hs1 ', description_kala=text) for text in ['first', 'second', 'first']]
    assert receipt_descriptions(sources) == {'HS1': 'first، second (۳ ردیف)'}


def test_single_description_and_empty_values():
    sources = [dict(hscode='A', description_kala=text) for text in [' one ', 'one', None]]
    sources += [dict(hscode='B', description_kala=None)]
    assert receipt_descriptions(sources) == {'A': 'one'}


def test_long_descriptions_are_not_truncated():
    text = 'a' * 5000
    result = receipt_descriptions([dict(hscode='A', description_kala=text), dict(hscode='A', description_kala='b')])
    assert result['A'] == text + '، b (۲ ردیف)'


def test_query_respects_live_allocated_rows_and_legacy_fallback():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE fa_ghabz_anbar_header (ID_ghabz INT, TALI_ID INT, IS_DELETED TEXT);
        CREATE TABLE FA_TALI_DETAILES (ID_TALI_DETAILS INT, ID_HEADERS_TALI INT, IS_DELETED TEXT, HSCODE TEXT, DESCRIPTION_KALA TEXT);
        CREATE TABLE FA_GHABZ_TALLY_SOURCE (RECEIPT_ID INT, TALLY_DETAIL_ID INT, QUANTITY_SHARE REAL, WEIGHT_SHARE REAL, BASKOL_SHARE REAL);
        INSERT INTO fa_ghabz_anbar_header VALUES (1,10,'no');
        INSERT INTO FA_TALI_DETAILES VALUES (1,10,'no','A','first'), (2,10,'no','A','second'), (3,10,'yes','A','deleted'), (4,11,'no','A','other tally');
    """)
    assert receipt_descriptions(map(dict, db.execute(DESCRIPTIONS_SQL, {'hid': 1}))) == {'A': 'first، second (۲ ردیف)'}
    db.executescript('INSERT INTO FA_GHABZ_TALLY_SOURCE VALUES (1,2,1,0,0), (1,1,0,0,0);')
    assert receipt_descriptions(map(dict, db.execute(DESCRIPTIONS_SQL, {'hid': 1}))) == {'A': 'second'}
    db.close()
