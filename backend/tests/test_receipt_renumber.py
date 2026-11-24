import sqlite3
import pytest
from fastapi import HTTPException
from app.services.tally_numbering import sync_receipt_numbers


@pytest.fixture
def db():
    c=sqlite3.connect(':memory:')
    c.executescript("""
    CREATE TABLE fa_ghabz_anbar_header (ID_ghabz INT, TALI_ID INT, GHABZ_NUMBER TEXT UNIQUE, GHABZ_SEQ INT, IS_MASTER TEXT, IS_DELETED TEXT, NUMBER_tali TEXT, MODIFY_AT TEXT, MODIFY_BY INT);
    CREATE TABLE FA_SORAT_HESAB_HEADER (TALI_ID_HEADER INT, ID_GHABZ_ANBAR INT, SORAT_IS_DELETED TEXT);
    INSERT INTO fa_ghabz_anbar_header VALUES (1,42,'1405_78',0,'yes','no','78',NULL,NULL),(2,42,'1405_78_2',2,'no','no','78',NULL,NULL),(3,42,'1404_78_1',1,'no','yes','78',NULL,NULL),(4,99,'1405_99',0,'yes','no','99',NULL,NULL);
    """)
    yield c
    c.close()


class Cursor:
    def __init__(self,c): self.c=c
    def execute(self,sql,params):
        self.cursor=self.c.execute(sql.replace(' FOR UPDATE','').replace('NVL(','COALESCE(').replace('SYSDATE','CURRENT_TIMESTAMP'),params)
    def fetchall(self): return self.cursor.fetchall()
    def fetchone(self): return self.cursor.fetchone()


def test_renumbers_active_receipts_preserving_year_and_sequence(db):
    sync_receipt_numbers(Cursor(db),42,'78.1','78',5)
    rows=db.execute('SELECT GHABZ_NUMBER,NUMBER_tali FROM fa_ghabz_anbar_header ORDER BY ID_ghabz').fetchall()
    assert rows==[('1405_78.1','78.1'),('1405_78.1_2','78.1'),('1404_78_1','78'),('1405_99','99')]


@pytest.mark.parametrize('owner,receipt',[(42,None),(None,2)])
def test_active_invoice_blocks_all_changes(db,owner,receipt):
    db.execute('INSERT INTO FA_SORAT_HESAB_HEADER VALUES (?, ?, ?)',(owner,receipt,'no'))
    with pytest.raises(HTTPException) as exc:
        sync_receipt_numbers(Cursor(db),42,'78.1','78',5)
    assert exc.value.status_code==409
    assert db.execute('SELECT GHABZ_NUMBER FROM fa_ghabz_anbar_header WHERE ID_ghabz=1').fetchone()[0]=='1405_78'


def test_cancelled_invoice_does_not_block(db):
    db.execute("INSERT INTO FA_SORAT_HESAB_HEADER VALUES (42,1,'yes')")
    sync_receipt_numbers(Cursor(db),42,'78.1','78',5)


def test_duplicate_receipt_number_prevents_partial_updates(db):
    db.execute("INSERT INTO fa_ghabz_anbar_header VALUES (5,99,'1405_78.1_2',2,'no','yes','78.1',NULL,NULL)")
    with pytest.raises(HTTPException):
        sync_receipt_numbers(Cursor(db),42,'78.1','78',5)
    assert db.execute('SELECT GHABZ_NUMBER FROM fa_ghabz_anbar_header WHERE ID_ghabz=1').fetchone()[0]=='1405_78'


def test_repairs_receipts_even_if_tally_already_has_new_number(db):
    sync_receipt_numbers(Cursor(db),42,'78.1','78.1',5)
    assert db.execute('SELECT GHABZ_NUMBER FROM fa_ghabz_anbar_header WHERE ID_ghabz=1').fetchone()[0]=='1405_78.1'
