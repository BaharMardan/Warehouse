from decimal import Decimal
from app.services.released_goods import build_report


def row(tid=1,sid=1,invoice=1,**kw):
    return dict(tally_id=tid,detail_id=sid,invoice_id=invoice,weight=100,quantity=10,
        row_pallets=10,receipt_pallets=2,weight_share=Decimal('.25'),quantity_share=Decimal('.2'),
        customs_value=1000,insured_value=5000,is_bimeh='yes',is_master='no',
        tally_pallets=10,pallet_quantity=2,**kw)


def test_partial_value_weight_and_exact_pallets():
    data=build_report([row()])
    r=data['rows'][0]
    assert (r['weight'],r['pallets'],r['customs_value'])==(25,2,250)
    assert data['totals']['tallies']==1


def test_insurance_and_tallies_count_once_across_rows_and_invoices():
    data=build_report([row(),row(sid=2),row(sid=1,invoice=2)])
    assert data['totals']['insured_value']==5000
    assert data['totals']['tallies']==1
    assert [r['insured_value'] for r in data['rows']]==[5000,None,None]


def test_zero_weight_uses_receipt_pallet_share():
    r=row();r['weight']=0
    assert build_report([r])['rows'][0]['customs_value']==200


def test_master_and_unknown_insurance():
    r=row();r.update(is_master='yes',weight_share=1,quantity_share=1,insured_value=None)
    data=build_report([r])
    assert data['rows'][0]['pallets']==10
    assert data['totals']['insurance_unknown']==1
    assert data['totals']['insured_value']==0


def test_no_insurance_is_zero_and_zero_exact_pallets_not_estimated():
    r=row();r.update(is_bimeh='no',receipt_pallets=0)
    data=build_report([r])
    assert data['totals']['insured_value']==0
    assert data['rows'][0]['pallets']==0
    assert not data['rows'][0]['pallets_estimated']


def test_estimated_pallets_are_explicit_and_duplicates_not_double_counted():
    r=row();r['receipt_pallets']=None
    data=build_report([r,r])
    assert len(data['rows'])==1
    assert data['rows'][0]['pallets']==Decimal('2.50')
    assert data['totals']['pallets_estimated']==1


def test_insurance_is_counted_once_for_each_distinct_tally():
    data=build_report([row(),row(tid=2,sid=2,invoice=2),row(tid=2,sid=3,invoice=2)])
    assert data['totals']['tallies']==2
    assert data['totals']['insured_value']==10000


def test_invoice_query_filters_issue_dates_cancellations_and_remaining_invoices():
    import sqlite3
    from app.routers.reports import RELEASE_INVOICES_SQL
    db=sqlite3.connect(':memory:')
    db.row_factory=sqlite3.Row
    db.executescript("""
        CREATE TABLE FA_SORAT_HESAB_HEADER (ID_SORAT INT, INVOICE_NUMBER INT, SORAT_CREATE_AT TEXT, ID_GHABZ_ANBAR INT, SORAT_IS_DELETED TEXT, BUYER_COMPANY_ID INT);
        CREATE TABLE fa_ghabz_anbar_header (ID_ghabz INT, GHABZ_NUMBER TEXT, TALI_ID INT, IS_MASTER TEXT, PALLET_QUANTITY INT, IS_DELETED TEXT);
        CREATE TABLE FA_TALI_HEADER (ID_TALI INT,TALI_NUMBER TEXT,IS_BIMEH TEXT,VOLUMETRIC_PALLETS INT,ID_PRODUCT_OWNEAR INT);
        CREATE TABLE FA_PRODUCT_OWNER (ID_OWNER INT,COMPANY_NAME TEXT,NAME TEXT,FAMILY TEXT);
        CREATE TABLE FA_TALI_DETAILES (ID_HEADERS_TALI INT,INSURED_VALUE REAL,IS_DELETED TEXT);
        CREATE TABLE FA_REMAINING_INVOICE (INVOICE_ID INT);
        INSERT INTO FA_TALI_HEADER VALUES (10,'78.1','yes',10,1);
        INSERT INTO FA_PRODUCT_OWNER VALUES (1,'Owner',NULL,NULL);
        INSERT INTO FA_TALI_DETAILES VALUES (10,5000,'no');
        INSERT INTO fa_ghabz_anbar_header VALUES (1,'R',10,'no',2,'no');
        INSERT INTO FA_SORAT_HESAB_HEADER (ID_SORAT,INVOICE_NUMBER,SORAT_CREATE_AT,ID_GHABZ_ANBAR,SORAT_IS_DELETED) VALUES
          (1,101,'2026-01-01 00:00:00',1,'no'),
          (2,102,'2026-01-02 00:00:00',1,'yes'),
          (3,103,'2026-01-03 00:00:00',1,'no'),
          (4,104,'2025-12-31 23:59:59',1,'no'),
          (5,105,'2026-02-01 00:00:00',1,'no'),
          (6,106,'2026-01-31 23:59:59',1,'no');
        INSERT INTO FA_REMAINING_INVOICE VALUES (3);
    """)
    sql=RELEASE_INVOICES_SQL.replace('NVL(','COALESCE(')
    records=db.execute(sql,{'start_at':'2026-01-01 00:00:00','end_before':'2026-02-01 00:00:00'}).fetchall()
    assert [r[0] for r in records]==[1,6]
    from app.services.income_report import filter_owner
    db.execute('UPDATE FA_TALI_HEADER SET ID_PRODUCT_OWNEAR=NULL')
    db.execute('UPDATE FA_SORAT_HESAB_HEADER SET BUYER_COMPANY_ID=1')
    params={'start_at':'2026-01-01 00:00:00','end_before':'2026-02-01 00:00:00'}
    fallback=[dict(r) for r in db.execute(sql,params)]
    assert len(filter_owner(fallback,1))==2
    assert fallback[0]['owner_name']=='Owner'
    db.execute('UPDATE FA_SORAT_HESAB_HEADER SET BUYER_COMPANY_ID=NULL')
    unknown=[dict(r) for r in db.execute(sql,params)]
    assert len(filter_owner(unknown,0))==2
    db.close()


def test_full_zero_weight_row_uses_its_own_pallet_allocation():
    r=row();r.update(weight=0,quantity_share=1,row_pallets=10,receipt_pallets=10,tally_pallets=100,pallet_quantity=10)
    assert build_report([r])['rows'][0]['customs_value']==1000


def test_legacy_zero_weight_row_estimate_uses_its_quantity_share():
    r=row();r.update(weight=0,quantity_share=1,row_pallets=10,receipt_pallets=None,tally_pallets=100,pallet_quantity=10)
    result=build_report([r])['rows'][0]
    assert result['customs_value']==1000
    assert result['pallets']==10
