from decimal import Decimal
from copy import deepcopy
import pytest
from app.services.receipt_layout import separate_lines


def grouped(**changes):
    return dict(id_ghabz_anbar_details=7, hscode='A', number_kala=10,
                weighte_asnad=100, weighte_baskol=90, description_kala='group', **changes)


def source(sid, **changes):
    base = dict(id=sid, hscode=' a ', description_kala='row '+str(sid),
                number_kala=10, weighte_asnad=100, weighte_baskol=90,
                code_kala=sid, goods_group_code=str(sid), type_basteh='box',
                id_tagh_anbar=sid, tagh_name=str(sid), number_hamel='carrier '+str(sid))
    return {**base, **changes}


def test_partial_sources_keep_original_metadata_and_totals():
    shares=[dict(id=1,quantity_share=Decimal('.3'),weight_share=Decimal('.4'),baskol_share=Decimal('.5')),
            dict(id=2,quantity_share=Decimal('.7'),weight_share=Decimal('.6'),baskol_share=Decimal('.5'))]
    result=separate_lines([grouped()], [source(1),source(2)], shares)
    assert [r['description_kala'] for r in result]==['row 1','row 2']
    assert [r['number_kala'] for r in result]==[3,7]
    assert [r['weighte_asnad'] for r in result]==[40,60]
    assert [r['weighte_baskol'] for r in result]==[45,45]
    assert result[1]['carriers']==['carrier 2']
    assert result[1]['goods_group_code']=='2'
    assert result[1]['id_ghabz_anbar_details']==7
    assert [r['source_row_id'] for r in result]==[1,2]


def test_master_uses_each_original_row_once_in_order():
    group=grouped(); group.update(number_kala=20,weighte_asnad=200,weighte_baskol=180)
    result=separate_lines([group],[source(2),source(1)],None)
    assert [r['source_row_id'] for r in result]==[2,1]
    assert sum(r['number_kala'] for r in result)==20


def test_zero_share_and_other_hs_are_excluded():
    shares=[dict(id=1,quantity_share=1,weight_share=1,baskol_share=1),
            dict(id=2,quantity_share=0,weight_share=0,baskol_share=0)]
    result=separate_lines([grouped()],[source(1),source(2),source(3,hscode='B')],shares)
    assert [r['source_row_id'] for r in result]==[1]


def test_missing_allocation_never_silently_changes_totals():
    with pytest.raises(ValueError):
        separate_lines([grouped()],[source(1)],[])
    with pytest.raises(ValueError):
        separate_lines([grouped()],[source(1)],[dict(id=1,quantity_share=Decimal('.5'),weight_share=1,baskol_share=1)])


def test_projection_does_not_mutate_financial_rows():
    rows=[grouped()]; before=deepcopy(rows)
    separate_lines(rows,[source(1)],None)
    assert rows==before


@pytest.mark.parametrize('fraction', [-1, 2, 'NaN'])
def test_invalid_shares_are_rejected(fraction):
    with pytest.raises(ValueError):
        separate_lines([grouped()],[source(1)],
            [dict(id=1,quantity_share=fraction,weight_share=1,baskol_share=1)])


def test_each_hs_group_preserves_its_own_total():
    rows=[grouped(), {**grouped(), 'hscode': 'B', 'id_ghabz_anbar_details': 8}]
    result=separate_lines(rows,[source(1),source(2,hscode='B')],None)
    assert [(r['hscode'],r['number_kala']) for r in result]==[('A',10),('B',10)]


def test_preference_defaults_off_and_can_be_saved_for_finalized_tally(monkeypatch):
    from unittest.mock import MagicMock
    from app.routers import tally_header as api
    state={'separate_rows': None}
    monkeypatch.setattr(api,'fetch_one',lambda *args: state)
    assert api.get_receipt_layout(10)=={'separate_rows': False}
    conn=MagicMock(); cur=conn.__enter__.return_value.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api,'get_connection',lambda: conn)
    monkeypatch.setattr(api.receipt_db,'lock_tally',lambda *args: {'id_tali':10})
    def save(sql,params):
        assert 'MERGE INTO' in sql
        assert params['tid']==10 and params['actor']==9
        state['separate_rows']=params['value']
    cur.execute.side_effect=save
    for chosen in (True,False):
        assert api.set_receipt_layout(10,api.ReceiptLayoutInput(separate_rows=chosen),{'id':9})=={'separate_rows':chosen}
        assert api.get_receipt_layout(10)=={'separate_rows':chosen}
    assert conn.__enter__.return_value.commit.call_count==2


def test_preference_rejects_missing_tally(monkeypatch):
    from fastapi import HTTPException
    from app.routers import tally_header as api
    monkeypatch.setattr(api,'fetch_one',lambda *args: None)
    with pytest.raises(HTTPException) as exc:
        api.get_receipt_layout(999)
    assert exc.value.status_code==404


def test_detail_endpoint_respects_saved_mode(monkeypatch):
    from app.routers import ghabz as api
    separate={'value':'yes'}
    def fetch(sql,params):
        if sql==api.DETAILS_SQL: return [grouped()]
        if sql==api.RECEIPT_LAYOUT_SQL: return [{'separate_rows':separate['value']}]
        if sql==api.DESCRIPTIONS_SQL: return [{'hscode':'A','description_kala':'original'}]
        return []
    monkeypatch.setattr(api,'fetch_all',fetch)
    monkeypatch.setattr(api,'separate_receipt_details',lambda hid,rows: [{'source_row_id':1}])
    assert api.list_ghabz_details(5)==[{'source_row_id':1}]
    separate['value']='no'
    result=api.list_ghabz_details(5)
    assert result[0]['description_kala']=='original'
    assert 'source_row_id' not in result[0]


def test_master_projection_reads_sources_without_child_allocation(monkeypatch):
    from unittest.mock import MagicMock
    from app.routers import ghabz as api
    from app.routers import receipt_workflow
    conn=MagicMock()
    monkeypatch.setattr(api,'get_connection',lambda:conn)
    monkeypatch.setattr(api.receipt_db,'receipt',lambda *args: ({'tally_id':10,'is_master':'yes'},[],None))
    monkeypatch.setattr(api.receipt_db,'rows',lambda *args:[source(1)])
    preview=MagicMock()
    monkeypatch.setattr(receipt_workflow,'preview_sources',preview)
    assert api.separate_receipt_details(5,[grouped()])[0]['source_row_id']==1
    preview.assert_not_called()


def test_child_projection_uses_existing_read_only_preview(monkeypatch):
    from unittest.mock import MagicMock
    from app.routers import ghabz as api
    from app.routers import receipt_workflow
    conn=MagicMock(); cur=conn.__enter__.return_value.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(api,'get_connection',lambda:conn)
    current={'tally_id':10,'is_master':'no'}; siblings=[current]
    monkeypatch.setattr(api.receipt_db,'receipt',lambda *args:(current,siblings,None))
    monkeypatch.setattr(api.receipt_db,'rows',lambda *args:[source(1)])
    preview=MagicMock(return_value=[dict(id=1,quantity_share=1,weight_share=1,baskol_share=1)])
    monkeypatch.setattr(receipt_workflow,'preview_sources',preview)
    assert api.separate_receipt_details(5,[grouped()])[0]['source_row_id']==1
    preview.assert_called_once_with(cur,current,siblings)
    cur.execute.assert_not_called()


def test_partial_receipt_never_shows_full_original_quantity():
    row={**grouped(),'number_kala':4,'weighte_asnad':40,'weighte_baskol':36}
    shares=[dict(id=1,quantity_share=Decimal('.4'),weight_share=Decimal('.4'),baskol_share=Decimal('.4'))]
    result=separate_lines([row],[source(1)],shares)
    assert (result[0]['number_kala'],result[0]['weighte_asnad'],result[0]['weighte_baskol'])==(4,40,36)


def test_layout_migration_preserves_financial_schema():
    import runpy
    from pathlib import Path
    from unittest.mock import MagicMock
    migration=runpy.run_path(str(Path(__file__).parents[1]/'migrations/versions/0006_receipt_row_layout.py'))
    cursor=MagicMock()
    migration['upgrade'](cursor)
    sql=cursor.execute.call_args.args[0]
    assert 'CREATE TABLE "FA_TALLY_RECEIPT_LAYOUT"' in sql
    assert "DEFAULT 'no'" in sql
    assert 'REFERENCES "FA_TALI_HEADER" ("ID_TALI")' in sql
    assert 'CHECK ("SEPARATE_ROWS" IN' in sql
    assert 'ALTER TABLE' not in sql and 'FA_ghabz_anbar_DETAILES' not in sql
