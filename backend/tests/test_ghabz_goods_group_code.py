"""Receipt display must use the public tariff code, preserving internal IDs."""
import sqlite3
import pytest
from app.routers.ghabz import DETAILS_SQL

@pytest.mark.parametrize("internal_id, public_code", [(29, "110"), (7, "101"), (30, "111")])
def test_details_resolve_public_group_code(internal_id, public_code):
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE FA_ghabz_anbar_DETAILES (
            ID_ghabz_anbar_DETAILS INT, ID_GHABZ_ANBAR_HEADAR INT,
            code_kala INT, code_kala_kantiner INT, DESCRIPTION_KALA TEXT,
            HSCODE TEXT, TYPE_BASTEh TEXT, NUMBER_KALA REAL, NUMBER_KAntiner REAL,
            WEIGHTE_asnad REAL, WEIGHTE_BASKOL REAL, NUMBER_HAMEL TEXT,
            ID_TAGH_ANBAR INT, IS_DELETED TEXT);
        CREATE TABLE FA_TAGH_ANBAR (ID_TAGH INT, NAME_TAGH TEXT);
        CREATE TABLE fa_kala_price (id_kala_price INT, CODE TEXT, IS_DELETED TEXT);
    """)
    # Even an archived tariff must still resolve on a historical receipt.
    db.execute("INSERT INTO fa_kala_price VALUES (?, ?, 'yes')", (internal_id, public_code))
    db.execute("INSERT INTO FA_ghabz_anbar_DETAILES (ID_ghabz_anbar_DETAILS, ID_GHABZ_ANBAR_HEADAR, code_kala, IS_DELETED) VALUES (1, 976, ?, 'no')", (internal_id,))
    row = dict(db.execute(DETAILS_SQL, {"hid":976}).fetchone())
    assert row["code_kala"] == internal_id
    assert row.get("goods_group_code") == public_code
    db.close()
